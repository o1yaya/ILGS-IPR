#!/usr/bin/env python3
"""Make reproducible 3D-OVS mask comparison plates for the seed-0 models."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


CASES = (
    ("bench", "Portuguese egg tart", "recovery"),
    ("blue_sofa", "sunglasses", "recovery"),
    ("office_desk", "a pack of pocket tissues", "recovery"),
    ("covered_desk", "gerbera", "limitations"),
    ("sofa", "Gundam", "limitations"),
)

COLORS = {
    "gt": (41, 104, 154),
    "official": (201, 91, 39),
    "ipr": (0, 128, 105),
    "ink": (28, 36, 43),
    "muted": (82, 94, 105),
}


def font(size, bold=False):
    names = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def mask_image(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        return image.convert("L")


def binary_mask(image, size=None):
    if size is not None and image.size != size:
        image = image.resize(size, Image.NEAREST)
    return np.asarray(image) > 128


def mask_iou(reference, prediction):
    gt = binary_mask(reference)
    pred = binary_mask(prediction, reference.size)
    union = np.logical_or(gt, pred).sum()
    return float(np.logical_and(gt, pred).sum() / union) if union else 0.0


def image_for_stem(folder, stem):
    for extension in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        path = folder / (stem + extension)
        if path.is_file():
            return path
    raise FileNotFoundError(f"No RGB image for {stem} in {folder}")


def case_views(scene, query, dataset_root, output_root, seed):
    dataset = dataset_root / scene
    manifest = json.loads((dataset / "ilgs_3dovs_layout.json").read_text(encoding="utf-8"))
    view_mapping = sorted(manifest["test_view_mapping"], key=lambda row: row["test_index"])
    if [row["test_index"] for row in view_mapping] != list(range(len(view_mapping))):
        raise ValueError(f"Non-contiguous test indices in {scene}")
    if query not in manifest["queries"]:
        raise ValueError(f"Query {query!r} is absent from {scene}/queries.txt")

    records = []
    for row in view_mapping:
        index = row["test_index"]
        paths = {
            variant: output_root / f"{scene}_ipr_{variant}_s{seed}"
            / "test/ours_30000_text/test_mask" / str(index) / f"{query}.png"
            for variant in ("official", "ipr")
        }
        gt_path = dataset / "test_mask" / str(index) / f"{query}.png"
        gt = mask_image(gt_path)
        official = mask_image(paths["official"])
        ipr = mask_image(paths["ipr"])
        official_iou = mask_iou(gt, official)
        ipr_iou = mask_iou(gt, ipr)
        records.append({
            "scene": scene,
            "query": query,
            "view_index": index,
            "image_stem": row["image_stem"],
            "rgb_path": image_for_stem(dataset / "images", row["image_stem"]),
            "gt_path": gt_path,
            "official_path": paths["official"],
            "ipr_path": paths["ipr"],
            "official_iou": official_iou,
            "ipr_iou": ipr_iou,
            "delta_iou": ipr_iou - official_iou,
        })
    if not records:
        raise ValueError(f"No test views for {scene}")
    median = sorted(records, key=lambda record: (record["delta_iou"], record["view_index"]))[
        len(records) // 2
    ]
    return records, median


def resized_canvas(rgb, mask, tile_width, image_height, color, gt_outline=None):
    scale = min(tile_width / rgb.width, image_height / rgb.height)
    size = (max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale)))
    rgb_small = rgb.resize(size, Image.BILINEAR)
    pixels = np.asarray(rgb_small).astype(np.float32).copy()
    selected = binary_mask(mask, size)
    tint = np.array(color, dtype=np.float32)
    pixels[selected] = pixels[selected] * 0.55 + tint * 0.45

    if gt_outline is not None:
        reference = gt_outline.resize(size, Image.NEAREST)
        dilated = np.asarray(reference.filter(ImageFilter.MaxFilter(5))) > 128
        eroded = np.asarray(reference.filter(ImageFilter.MinFilter(3))) > 128
        pixels[np.logical_and(dilated, ~eroded)] = (255, 255, 255)

    rendered = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    canvas = Image.new("RGB", (tile_width, image_height), "white")
    canvas.paste(rendered, ((tile_width - size[0]) // 2, (image_height - size[1]) // 2))
    return canvas


def draw_wrapped(draw, text, x, y, max_width, text_font, fill, line_height):
    words = text.split()
    line = ""
    for word in words:
        candidate = word if not line else line + " " + word
        if draw.textbbox((0, 0), candidate, font=text_font)[2] > max_width and line:
            draw.text((x, y), line, font=text_font, fill=fill)
            y += line_height
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=text_font, fill=fill)
        y += line_height
    return y


def make_plate(records, path_prefix, title, footer, tile_width=420):
    margin = 34
    label_width = 255
    gap = 13
    image_height = 315
    row_height = image_height + 58
    header_height = 112
    footer_height = 52
    width = 2 * margin + label_width + gap + 4 * tile_width + 3 * gap
    height = header_height + len(records) * row_height + footer_height
    plate = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(plate)
    ink = COLORS["ink"]
    muted = COLORS["muted"]
    title_font = font(33, bold=True)
    heading_font = font(25, bold=True)
    label_font = font(25, bold=True)
    body_font = font(22)
    caption_font = font(24)

    draw.text((margin, 16), title, font=title_font, fill=ink)
    x0 = margin + label_width + gap
    for column, heading in enumerate(("RGB", "Ground truth", "Controlled ILGS", "IPR")):
        draw.text((x0 + column * (tile_width + gap), 70), heading, font=heading_font, fill=ink)
    draw.line((margin, 105, width - margin, 105), fill=(190, 198, 203), width=2)

    for row_number, record in enumerate(records):
        y = header_height + row_number * row_height
        scene = record["scene"].replace("_", " ")
        draw.text((margin, y + 7), scene, font=label_font, fill=ink)
        end_y = draw_wrapped(draw, record.get("display_query", record["query"]), margin, y + 45,
                             label_width - 10, body_font, ink, 30)
        draw.text((margin, end_y + 13), f'View {record["view_index"]}',
                  font=body_font, fill=muted)
        draw.text((margin, end_y + 48), f'Delta IoU {record["delta_iou"]:+.3f}',
                  font=body_font, fill=COLORS["ipr"] if record["delta_iou"] >= 0 else COLORS["official"])

        with Image.open(record["rgb_path"]) as source:
            rgb = source.convert("RGB")
        gt = mask_image(record["gt_path"])
        official = mask_image(record["official_path"])
        ipr = mask_image(record["ipr_path"])
        scale = min(tile_width / rgb.width, image_height / rgb.height)
        size = (max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale)))
        plain = Image.new("RGB", (tile_width, image_height), "white")
        rgb_small = rgb.resize(size, Image.BILINEAR)
        plain.paste(rgb_small, ((tile_width - size[0]) // 2, (image_height - size[1]) // 2))
        panels = (
            plain,
            resized_canvas(rgb, gt, tile_width, image_height, COLORS["gt"]),
            resized_canvas(rgb, official, tile_width, image_height,
                           COLORS["official"], gt_outline=gt),
            resized_canvas(rgb, ipr, tile_width, image_height,
                           COLORS["ipr"], gt_outline=gt),
        )
        for column, panel in enumerate(panels):
            x = x0 + column * (tile_width + gap)
            plate.paste(panel, (x, y))
        captions = (
            record["image_stem"],
            "Reference mask",
            f'IoU {record["official_iou"]:.3f}',
            f'IoU {record["ipr_iou"]:.3f}',
        )
        for column, caption in enumerate(captions):
            x = x0 + column * (tile_width + gap)
            draw.text((x + 3, y + image_height + 13), caption,
                      font=caption_font, fill=muted)
        if row_number < len(records) - 1:
            draw.line((margin, y + row_height - 2, width - margin, y + row_height - 2),
                      fill=(226, 230, 232), width=1)

    draw.text((margin, height - 39), footer, font=font(20), fill=muted)
    plate.save(str(path_prefix) + ".png", dpi=(300, 300))
    plate.save(str(path_prefix) + ".pdf", "PDF", resolution=300.0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset_root", type=Path, default=Path("dataset/3dovs"))
    parser.add_argument("--output_root", type=Path, default=Path("output/3dovs"))
    parser.add_argument("--out_dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    selected = {"recovery": [], "limitations": []}
    for scene, query, group in CASES:
        all_views, representative = case_views(
            scene, query, args.dataset_root, args.output_root, args.seed
        )
        selected[group].append(representative)
        selections = {id(representative): "median"}
        if scene == "covered_desk":
            representative["display_query"] = "gerbera (typical view)"
            worst = min(all_views, key=lambda record: (record["delta_iou"], record["view_index"]))
            if worst is not representative:
                worst["display_query"] = "gerbera (worst view)"
                selected[group].append(worst)
                selections[id(worst)] = "worst"
        for record in all_views:
            rows.append({
                "scene": scene,
                "query": query,
                "view_index": record["view_index"],
                "image_stem": record["image_stem"],
                "official_iou": record["official_iou"],
                "ipr_iou": record["ipr_iou"],
                "delta_iou": record["delta_iou"],
                "selected_for": selections.get(id(record), ""),
            })
        print(f'{scene}: view {representative["view_index"]}, '
              f'IoU {representative["official_iou"]:.3f} -> {representative["ipr_iou"]:.3f}')

    with (args.out_dir / "case_view_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    make_plate(selected["recovery"], args.out_dir / "fig_3dovs_recovery",
               f"Recovery of class-level failures (seed {args.seed})",
               "Median per-view IoU change selected; white contours mark GT boundaries in predictions.")
    make_plate(selected["limitations"], args.out_dir / "fig_3dovs_limitations",
               f"Remaining failure cases (seed {args.seed})",
               "Typical and worst gerbera views; median Gundam view. White contours mark GT boundaries.")
    print(f"Figures and per-view metrics: {args.out_dir}")


if __name__ == "__main__":
    main()
