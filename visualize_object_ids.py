import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}


def stable_color(object_id):
    """Deterministic high-contrast-ish color for an integer id."""
    x = int(object_id) + 1
    r = (37 * x + 67) % 256
    g = (17 * x + 149) % 256
    b = (97 * x + 29) % 256
    if r + g + b < 120:
        r = (r + 120) % 256
        g = (g + 80) % 256
    return int(r), int(g), int(b)


def load_font(size):
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def find_rgb_for_mask(mask_path, image_dir):
    if image_dir is None:
        return None
    stem = mask_path.stem
    for ext in IMAGE_EXTS:
        candidate = image_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    # LERF masks/images are often frame_00001.png vs frame_00001.jpg.
    matches = sorted(image_dir.glob(f"{stem}.*"))
    for candidate in matches:
        if candidate.suffix.lower() in IMAGE_EXTS:
            return candidate
    return None


def make_id_canvas(label):
    color = np.zeros((*label.shape, 3), dtype=np.uint8)
    for object_id in np.unique(label):
        color[label == object_id] = stable_color(object_id)
    return Image.fromarray(color)


def alpha_overlay(rgb, id_map, alpha):
    rgb = rgb.convert("RGB")
    if rgb.size != id_map.size:
        rgb = rgb.resize(id_map.size, Image.BILINEAR)
    return Image.blend(rgb, id_map.convert("RGB"), alpha)


def draw_component_labels(image, label, font, min_area, max_components_per_id):
    draw = ImageDraw.Draw(image)
    rows = []

    for object_id in sorted(int(x) for x in np.unique(label)):
        mask = label == object_id
        total_area = int(mask.sum())
        components, count = ndimage.label(mask)
        component_rows = []

        for component_id in range(1, count + 1):
            component = components == component_id
            area = int(component.sum())
            if area < min_area:
                continue
            ys, xs = np.nonzero(component)
            if xs.size == 0:
                continue
            cy, cx = int(np.median(ys)), int(np.median(xs))
            component_rows.append((area, cx, cy))

        component_rows.sort(reverse=True)
        for rank, (area, cx, cy) in enumerate(component_rows[:max_components_per_id], start=1):
            text = str(object_id)
            bbox = draw.textbbox((cx, cy), text, font=font)
            pad = 3
            x0 = cx - (bbox[2] - bbox[0]) // 2 - pad
            y0 = cy - (bbox[3] - bbox[1]) // 2 - pad
            x1 = cx + (bbox[2] - bbox[0]) // 2 + pad
            y1 = cy + (bbox[3] - bbox[1]) // 2 + pad
            draw.rectangle((x0, y0, x1, y1), fill=(255, 255, 255), outline=(0, 0, 0))
            draw.text((x0 + pad, y0 + pad - 1), text, fill=(0, 0, 0), font=font)
            rows.append(
                {
                    "object_id": object_id,
                    "total_pixels": total_area,
                    "component_rank": rank,
                    "component_pixels": area,
                    "label_x": cx,
                    "label_y": cy,
                }
            )

        if not component_rows:
            rows.append(
                {
                    "object_id": object_id,
                    "total_pixels": total_area,
                    "component_rank": "",
                    "component_pixels": "",
                    "label_x": "",
                    "label_y": "",
                }
            )

    return rows


def add_legend(image, label, font):
    ids = sorted(int(x) for x in np.unique(label))
    counts = {object_id: int((label == object_id).sum()) for object_id in ids}

    line_h = 22
    margin = 12
    legend_w = 220
    legend_h = max(image.height, margin * 2 + line_h * (len(ids) + 1))
    canvas = Image.new("RGB", (image.width + legend_w, legend_h), (255, 255, 255))
    canvas.paste(image.convert("RGB"), (0, 0))

    draw = ImageDraw.Draw(canvas)
    x = image.width + margin
    y = margin
    draw.text((x, y), "object id / pixels", fill=(0, 0, 0), font=font)
    y += line_h
    for object_id in ids:
        color = stable_color(object_id)
        draw.rectangle((x, y + 4, x + 14, y + 18), fill=color, outline=(0, 0, 0))
        draw.text((x + 22, y), f"{object_id}: {counts[object_id]}", fill=(0, 0, 0), font=font)
        y += line_h
    return canvas


def collect_masks(mask_dir, frames):
    masks = sorted(p for p in mask_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if frames:
        wanted = set(frames)
        masks = [p for p in masks if p.stem in wanted or p.name in wanted]
    return masks


def visualize_one(mask_path, image_dir, output_dir, alpha, font, min_label_area, max_components_per_id):
    label = np.array(Image.open(mask_path))
    id_map = make_id_canvas(label)

    labeled_id_map = id_map.copy()
    rows = draw_component_labels(labeled_id_map, label, font, min_label_area, max_components_per_id)
    labeled_id_map = add_legend(labeled_id_map, label, font)

    output_dir.mkdir(parents=True, exist_ok=True)
    id_out = output_dir / f"{mask_path.stem}_object_ids.png"
    labeled_id_map.save(id_out)

    overlay_out = None
    rgb_path = find_rgb_for_mask(mask_path, image_dir)
    if rgb_path is not None:
        rgb = Image.open(rgb_path)
        overlay = alpha_overlay(rgb, id_map, alpha)
        draw_component_labels(overlay, label, font, min_label_area, max_components_per_id)
        overlay = add_legend(overlay, label, font)
        overlay_out = output_dir / f"{mask_path.stem}_object_ids_overlay.png"
        overlay.save(overlay_out)

    return rows, id_out, overlay_out


def main():
    parser = argparse.ArgumentParser(description="Visualize object ids from object_mask/object_mask_refined.")
    parser.add_argument("--dataset_path", type=Path, required=True, help="Scene directory, e.g. dataset/lerf/ramen")
    parser.add_argument("--mask_dir", type=str, default="object_mask_refined", help="Mask folder name or absolute path")
    parser.add_argument("--image_dir", type=str, default="images", help="RGB image folder name or absolute path")
    parser.add_argument("--output_dir", type=str, default="object_mask_id_vis", help="Output folder name or absolute path")
    parser.add_argument("--frames", nargs="*", default=None, help="Optional frame stems/names, e.g. frame_00001 frame_00020.png")
    parser.add_argument("--limit", type=int, default=0, help="Visualize only the first N masks; 0 means all")
    parser.add_argument("--alpha", type=float, default=0.55, help="ID color opacity in RGB overlay")
    parser.add_argument("--font_size", type=int, default=15)
    parser.add_argument("--min_label_area", type=int, default=120, help="Only draw id text on components at least this large")
    parser.add_argument("--max_components_per_id", type=int, default=3)
    args = parser.parse_args()

    dataset_path = args.dataset_path
    mask_dir = Path(args.mask_dir)
    if not mask_dir.is_absolute():
        mask_dir = dataset_path / mask_dir
    image_dir = Path(args.image_dir)
    if not image_dir.is_absolute():
        image_dir = dataset_path / image_dir
    if not image_dir.exists():
        image_dir = None

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = dataset_path / output_dir

    if not mask_dir.exists():
        raise FileNotFoundError(f"Mask directory not found: {mask_dir}")

    masks = collect_masks(mask_dir, args.frames)
    if args.limit > 0:
        masks = masks[: args.limit]
    if not masks:
        raise FileNotFoundError(f"No mask images found in {mask_dir}")

    font = load_font(args.font_size)
    summary_rows = []
    for mask_path in masks:
        rows, id_out, overlay_out = visualize_one(
            mask_path,
            image_dir,
            output_dir,
            args.alpha,
            font,
            args.min_label_area,
            args.max_components_per_id,
        )
        for row in rows:
            row["image"] = mask_path.name
            summary_rows.append(row)
        print(f"saved: {id_out}")
        if overlay_out is not None:
            print(f"saved: {overlay_out}")

    csv_path = output_dir / "object_id_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["image", "object_id", "total_pixels", "component_rank", "component_pixels", "label_x", "label_y"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"summary: {csv_path}")


if __name__ == "__main__":
    main()
