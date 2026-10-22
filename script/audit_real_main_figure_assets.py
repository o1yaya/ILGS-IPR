#!/usr/bin/env python3
"""Audit protocol-aligned figure assets and render contact sheets for QA."""

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


LABEL_COLORS = np.array(
    [
        [225, 229, 235],
        [33, 102, 172],
        [178, 24, 43],
        [27, 120, 55],
        [241, 163, 64],
        [118, 42, 131],
        [67, 147, 195],
        [214, 96, 77],
    ],
    dtype=np.uint8,
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size=size)


def load_binary(path: Path, size=None) -> np.ndarray:
    image = Image.open(path).convert("L")
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image) >= 128


def iou(prediction: np.ndarray, target: np.ndarray) -> float:
    union = np.logical_or(prediction, target).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(prediction, target).sum() / union)


def colorize_labels(labels: np.ndarray) -> Image.Image:
    return Image.fromarray(LABEL_COLORS[labels % len(LABEL_COLORS)])


def reliability_rgb(values: np.ndarray) -> Image.Image:
    t = values.astype(np.float32) / 255.0
    low = np.array([8, 48, 107], dtype=np.float32)
    mid = np.array([107, 174, 214], dtype=np.float32)
    high = np.array([247, 251, 255], dtype=np.float32)
    first = np.minimum(t * 2.0, 1.0)[..., None]
    second = np.maximum(t * 2.0 - 1.0, 0.0)[..., None]
    rgb = low * (1.0 - first) + mid * first
    rgb = rgb * (1.0 - second) + high * second
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.convert("RGB")
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return canvas


def changed_crop(raw: np.ndarray, clean: np.ndarray) -> Image.Image:
    changed = raw != clean
    yy, xx = np.where(changed)
    if len(xx) == 0:
        return Image.new("RGB", (640, 480), "white")
    pad = max(60, int(max(xx.max() - xx.min(), yy.max() - yy.min()) * 0.25))
    x0, x1 = max(0, int(xx.min()) - pad), min(raw.shape[1], int(xx.max()) + pad + 1)
    y0, y1 = max(0, int(yy.min()) - pad), min(raw.shape[0], int(yy.max()) + pad + 1)
    before = np.asarray(colorize_labels(raw[y0:y1, x0:x1]))
    after = np.asarray(colorize_labels(clean[y0:y1, x0:x1]))
    spacer = np.full((before.shape[0], 12, 3), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([before, spacer, after], axis=1))


def make_training_sheet(scene_root: Path, rows: list[dict], output: Path) -> None:
    width, tile_width, tile_height = 1800, 320, 240
    margin, gap, label_height = 40, 24, 54
    columns = ["RGB training view", "Noisy identity labels", "Cleaned labels", "Reliability W(p)", "Cleanup zoom: before | after"]
    height = margin * 2 + 70 + len(rows) * (tile_height + label_height + gap)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 22), scene_root.name.replace("_", " ").title(), font=font(32, True), fill=BLACK)
    for column, title in enumerate(columns):
        x = margin + column * (tile_width + gap)
        draw.text((x + tile_width // 2, 74), title, font=font(19, True), fill=BLACK, anchor="ma")

    for row_index, row in enumerate(rows):
        stem = row["stem"]
        frame = scene_root / "training_frames" / stem
        raw = np.asarray(Image.open(frame / "noisy_identity_labels.png"))
        clean = np.asarray(Image.open(frame / "cleaned_identity_labels.png"))
        confidence = np.asarray(Image.open(frame / "reliability_map.png").convert("L"))
        rgb_path = next(frame.glob("rgb.*"))
        panels = [
            Image.open(rgb_path),
            colorize_labels(raw),
            colorize_labels(clean),
            reliability_rgb(confidence),
            changed_crop(raw, clean),
        ]
        y = 118 + row_index * (tile_height + label_height + gap)
        for column, panel in enumerate(panels):
            x = margin + column * (tile_width + gap)
            canvas.paste(fit(panel, (tile_width, tile_height)), (x, y))
        description = (
            f"frame {stem}   changed={row['changed_pixel_ratio'] * 100:.4f}%   "
            f"low-W={row['low_reliability_pixel_ratio'] * 100:.1f}%   "
            f"mean W={row['mean_reliability']:.3f}"
        )
        draw.text((margin, y + tile_height + 12), description, font=font(19), fill="#455A64")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def audit_queries(scene_root: Path) -> dict:
    gt_root = scene_root / "dataset" / "test_mask"
    official_root = scene_root / "models" / "official" / "test" / "test_mask"
    ipr_root = scene_root / "models" / "ipr" / "test" / "test_mask"
    records = []
    for view_dir in sorted(gt_root.iterdir(), key=lambda path: int(path.name)):
        if not view_dir.is_dir():
            continue
        for gt_path in sorted(view_dir.glob("*.png")):
            official_path = official_root / view_dir.name / gt_path.name
            ipr_path = ipr_root / view_dir.name / gt_path.name
            if not official_path.is_file() or not ipr_path.is_file():
                continue
            gt_image = Image.open(gt_path).convert("L")
            gt = np.asarray(gt_image) >= 128
            official = load_binary(official_path, gt_image.size)
            ipr = load_binary(ipr_path, gt_image.size)
            official_iou = iou(official, gt)
            ipr_iou = iou(ipr, gt)
            records.append(
                {
                    "view": int(view_dir.name),
                    "query": gt_path.stem,
                    "official_iou": official_iou,
                    "ipr_iou": ipr_iou,
                    "delta_iou": ipr_iou - official_iou,
                }
            )
    by_query = {}
    for query in sorted({record["query"] for record in records}):
        query_records = [record for record in records if record["query"] == query]
        by_query[query] = {
            "mean_official_iou": float(np.mean([r["official_iou"] for r in query_records])),
            "mean_ipr_iou": float(np.mean([r["ipr_iou"] for r in query_records])),
            "mean_delta_iou": float(np.mean([r["delta_iou"] for r in query_records])),
            "views": query_records,
        }
    ranking = sorted(
        by_query.items(), key=lambda item: item[1]["mean_delta_iou"], reverse=True
    )
    selected_query, selected_summary = ranking[0]
    positive_views = [
        record for record in selected_summary["views"] if record["delta_iou"] > 0
    ]
    candidates = positive_views or selected_summary["views"]
    selected_view = min(
        candidates,
        key=lambda record: abs(record["delta_iou"] - selected_summary["mean_delta_iou"]),
    )
    return {
        "records": records,
        "queries": by_query,
        "ranking": [query for query, _ in ranking],
        "selected": {"query": selected_query, **selected_view},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    report = {
        "protocol": manifest["protocol"],
        "seed": manifest["seed"],
        "manual_mask_editing": manifest["manual_mask_editing"],
        "scenes": {},
    }
    for scene, scene_manifest in manifest["scenes"].items():
        scene_root = args.root / scene
        training_rows = scene_manifest["selected_training_frames"]
        make_training_sheet(
            scene_root,
            training_rows,
            args.output / f"{scene}_training_audit.png",
        )
        report["scenes"][scene] = {
            "training_frames": training_rows,
            "query_evaluation": audit_queries(scene_root),
        }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "real_asset_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for scene, data in report["scenes"].items():
        selection = data["query_evaluation"]["selected"]
        print(
            scene,
            selection["query"],
            f"view={selection['view']}",
            f"official={selection['official_iou']:.3f}",
            f"ipr={selection['ipr_iou']:.3f}",
            f"delta={selection['delta_iou']:+.3f}",
        )


if __name__ == "__main__":
    main()
