import argparse
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


DEFAULT_CASES = {
    "teatime": [
        ("0", "sheep"),
        ("0", "spoon handle"),
        ("2", "plate"),
        ("0", "cookies on a plate"),
    ],
    "ramen": [
        ("1", "pork belly"),
        ("0", "glass of water"),
        ("2", "egg"),
        ("2", "chopsticks"),
    ],
    "figurines": [
        ("2", "red toy chair"),
        ("3", "old camera"),
        ("2", "rubber duck with red hat"),
        ("1", "green apple"),
    ],
}


COLORS = {
    "gt": (255, 70, 70),
    "official": (255, 88, 70),
    "ipr": (252, 183, 62),
    "full_refine": (85, 220, 170),
    "seed_ref": (88, 185, 255),
    "part_refine": (190, 92, 255),
}


def safe_name(text):
    return text.replace("/", "_").replace("\\", "_").replace(" ", "_")


def load_font(size=18):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_text(text, max_chars=18):
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def open_rgb(path, size=None):
    img = Image.open(path).convert("RGB")
    if size is not None and img.size != size:
        img = img.resize(size, Image.BILINEAR)
    return img


def open_mask(path, size):
    if path is None or not Path(path).exists():
        return None
    mask = Image.open(path).convert("L")
    if mask.size != size:
        mask = mask.resize(size, Image.NEAREST)
    return np.array(mask) > 128


def overlay(rgb, mask, color, alpha=0.48):
    out = np.array(rgb).astype(np.float32)
    if mask is not None:
        color_arr = np.array(color, dtype=np.float32)
        out[mask] = out[mask] * (1.0 - alpha) + color_arr * alpha
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def iou(mask_a, mask_b):
    if mask_a is None or mask_b is None:
        return None
    inter = np.logical_and(mask_a, mask_b).sum()
    union = np.logical_or(mask_a, mask_b).sum()
    if union == 0:
        return 0.0
    return float(inter / union)


def find_render(base, idx):
    roots = [
        base / "renders",
        base / "rgb",
    ]
    names = [
        f"{int(idx):05d}.png",
        f"{int(idx):05d}.jpg",
        f"{idx}.png",
        f"{idx}.jpg",
    ]
    for root in roots:
        for name in names:
            path = root / name
            if path.exists():
                return path
    return None


def mask_path(root, idx, query):
    candidates = [
        root / str(int(idx)) / f"{query}.png",
        root / str(idx) / f"{query}.png",
        root / str(int(idx)) / f"{query.replace(' ', '_')}.png",
        root / str(idx) / f"{query.replace(' ', '_')}.png",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def make_tile(image, title, subtitle=None, width=260):
    ratio = width / image.width
    height = max(1, int(image.height * ratio))
    image = image.resize((width, height), Image.BILINEAR)
    title_h = 52
    tile = Image.new("RGB", (width, height + title_h), "white")
    tile.paste(image, (0, title_h))
    draw = ImageDraw.Draw(tile)
    font = load_font(15)
    small = load_font(12)
    draw.text((4, 4), title, fill=(20, 20, 20), font=font)
    if subtitle:
        draw.text((4, 25), subtitle, fill=(80, 80, 80), font=small)
    return tile


def make_blank_tile(title, subtitle="not used", width=260, height=190):
    title_h = 52
    tile = Image.new("RGB", (width, height + title_h), "white")
    draw = ImageDraw.Draw(tile)
    font = load_font(15)
    small = load_font(12)
    draw.text((4, 4), title, fill=(20, 20, 20), font=font)
    if subtitle:
        draw.text((4, 25), subtitle, fill=(130, 130, 130), font=small)
    x0, y0 = 8, title_h + 8
    x1, y1 = width - 8, height + title_h - 8
    draw.rectangle((x0, y0, x1, y1), outline=(220, 220, 220), width=1)
    draw.line((x0, y0, x1, y1), fill=(220, 220, 220), width=1)
    draw.line((x0, y1, x1, y0), fill=(220, 220, 220), width=1)
    return tile


def hstack(tiles, gap=10, row_height=None):
    w = sum(t.width for t in tiles) + gap * (len(tiles) - 1)
    h = row_height or max(t.height for t in tiles)
    out = Image.new("RGB", (w, h), "white")
    x = 0
    for tile in tiles:
        out.paste(tile, (x, 0))
        x += tile.width + gap
    return out


def vstack(rows, gap=18, left_labels=None, label_w=190):
    label_w = label_w if left_labels else 0
    w = max(r.width for r in rows) + label_w
    h = sum(r.height for r in rows) + gap * (len(rows) - 1)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    draw = ImageDraw.Draw(out)
    font = load_font(14)
    for i, row in enumerate(rows):
        if left_labels:
            label_lines = left_labels[i].split("\n")
            yy = y + 10
            for line in label_lines:
                draw.text((6, yy), line, fill=(50, 50, 50), font=font)
                yy += 20
        out.paste(row, (label_w, y))
        y += row.height + gap
    return out


def build_comparison_figure(scene, cases, dataset_root, output_root, out_dir, tile_width):
    dataset_path = dataset_root / scene
    official_base = output_root / scene / "test" / "ours_30000_text"
    ipr_base = output_root / f"{scene}_refined_masks" / "test" / "ours_30000_text"

    rows = []
    labels = []
    for idx, query in cases:
        render_path = find_render(ipr_base, idx) or find_render(official_base, idx)
        if render_path is None:
            print(f"[WARN] render missing: scene={scene}, idx={idx}")
            continue

        rgb = open_rgb(render_path)
        size = rgb.size
        gt = open_mask(mask_path(dataset_path / "test_mask", idx, query), size)
        official = open_mask(mask_path(official_base / "test_mask", idx, query), size)
        ipr_full = open_mask(mask_path(ipr_base / "test_mask", idx, query), size)

        # If the IPR-only mask has been saved separately, use it. Otherwise this
        # column is omitted to avoid duplicating full-refine by accident.
        ipr_only_root = ipr_base / "test_mask_ipr_only"
        ipr_only = None
        has_ipr_only_column = ipr_only_root.exists()
        if ipr_only_root.exists():
            ipr_only = open_mask(mask_path(ipr_only_root, idx, query), size)

        tiles = [
            make_tile(rgb, "RGB", width=tile_width),
            make_tile(overlay(rgb, gt, COLORS["gt"]), "GT", width=tile_width),
            make_tile(
                overlay(rgb, official, COLORS["official"]),
                "Official-fixed",
                f"IoU={iou(gt, official):.3f}" if iou(gt, official) is not None else "missing",
                width=tile_width,
            ),
        ]
        if has_ipr_only_column:
            tiles.append(
                make_tile(
                    overlay(rgb, ipr_only, COLORS["ipr"]),
                    "IPR",
                    f"IoU={iou(gt, ipr_only):.3f}" if iou(gt, ipr_only) is not None else "missing",
                    width=tile_width,
                )
            )
        tiles.append(
            make_tile(
                overlay(rgb, ipr_full, COLORS["full_refine"]),
                "IPR + Full-refine",
                f"IoU={iou(gt, ipr_full):.3f}" if iou(gt, ipr_full) is not None else "missing",
                width=tile_width,
            )
        )
        rows.append(hstack(tiles, row_height=max(t.height for t in tiles)))
        labels.append("\n".join([scene, f"view {idx}", *wrap_text(query, 18)]))

    if not rows:
        return None
    fig = vstack(rows, left_labels=labels)
    out_path = out_dir / f"fig_{scene}_mask_comparison.png"
    fig.save(out_path)
    return out_path


def build_candidate_debug(scene, cases, output_root, dataset_root, out_dir, tile_width, only_part_cases=False):
    ipr_base = output_root / f"{scene}_refined_masks" / "test" / "ours_30000_text"
    if not ipr_base.exists():
        return None

    has_part_refine = False
    part_root = ipr_base / "test_mask_full_part_refine"
    cases_with_part = []
    for idx, query in cases:
        if mask_path(part_root, idx, query).exists():
            has_part_refine = True
            cases_with_part.append((idx, query))
    if only_part_cases and cases_with_part:
        cases = cases_with_part

    rows = []
    labels = []
    for idx, query in cases:
        render_path = find_render(ipr_base, idx)
        if render_path is None:
            continue
        rgb = open_rgb(render_path)
        size = rgb.size
        gt = open_mask(mask_path(dataset_root / scene / "test_mask", idx, query), size)

        candidate_roots = [
            ("GT", dataset_root / scene / "test_mask", "gt"),
            ("Full official", ipr_base / "test_mask_full_official", "official"),
            ("Seed-ref", ipr_base / "test_mask_full_seed_ref", "seed_ref"),
            ("Selected", ipr_base / "test_mask", "full_refine"),
        ]
        if has_part_refine:
            candidate_roots.insert(
                3,
                ("Part-refine", ipr_base / "test_mask_full_part_refine", "part_refine"),
            )
        tiles = [make_tile(rgb, "RGB", width=tile_width)]
        for title, root, color_key in candidate_roots:
            mask = open_mask(mask_path(root, idx, query), size)
            if mask is None and title == "Part-refine":
                # Keep alignment only when this scene has at least one true
                # part-refine case. Use a quiet placeholder for non-part rows.
                tiles.append(make_blank_tile(title, "not applicable", width=tile_width, height=tiles[0].height - 52))
                continue
            subtitle = None
            if title != "GT":
                val = iou(gt, mask)
                subtitle = f"IoU={val:.3f}" if val is not None else "missing"
            tiles.append(make_tile(overlay(rgb, mask, COLORS[color_key]), title, subtitle, width=tile_width))
        rows.append(hstack(tiles, row_height=max(t.height for t in tiles)))
        labels.append("\n".join([scene, f"view {idx}", *wrap_text(query, 18)]))

    if not rows:
        return None
    fig = vstack(rows, left_labels=labels)
    out_path = out_dir / f"fig_{scene}_full_refine_candidates.png"
    fig.save(out_path)
    return out_path


def parse_case(text):
    parts = text.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"case must be scene:view:query, got {text}")
    return parts[0], parts[1], parts[2]


def main():
    parser = argparse.ArgumentParser(
        description="Generate paper-ready debug figures for IPR / full-refine results."
    )
    parser.add_argument("--dataset_root", default="dataset/lerf")
    parser.add_argument("--output_root", default="output/lerf")
    parser.add_argument("--out_dir", default="paper_figures")
    parser.add_argument(
        "--scene",
        choices=["teatime", "ramen", "figurines", "all"],
        default="all",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Custom case in format scene:view:query. Can be repeated.",
    )
    parser.add_argument("--tile_width", type=int, default=260)
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="Also generate official/seed-ref/part-refine candidate comparison figures. "
             "Requires running full-refine with --save_candidates.",
    )
    parser.add_argument(
        "--only_part_cases",
        action="store_true",
        help="For candidate figures, keep only cases that actually have a Part-refine mask. "
             "Useful for clean paper figures without not-applicable placeholders.",
    )
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    output_root = Path(args.output_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.case:
        by_scene = {}
        for item in args.case:
            scene, idx, query = parse_case(item)
            by_scene.setdefault(scene, []).append((idx, query))
    else:
        scenes = ["teatime", "ramen", "figurines"] if args.scene == "all" else [args.scene]
        by_scene = {scene: DEFAULT_CASES[scene] for scene in scenes}

    outputs = []
    for scene, cases in by_scene.items():
        path = build_comparison_figure(
            scene, cases, dataset_root, output_root, out_dir, args.tile_width
        )
        if path is not None:
            outputs.append(path)
            print(f"Saved: {path}")
        if args.candidates:
            path = build_candidate_debug(
                scene, cases, output_root, dataset_root, out_dir, args.tile_width, args.only_part_cases
            )
            if path is not None:
                outputs.append(path)
                print(f"Saved: {path}")

    if not outputs:
        print("No figures generated. Check render/mask paths.")


if __name__ == "__main__":
    main()
