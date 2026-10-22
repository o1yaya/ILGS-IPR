#!/usr/bin/env python3
"""Export high-contrast large-region identity examples for an IPR method figure.

The script supports both a normal server scene directory and the compact artifact
bundle exported by export_ipr_method_assets.py. It never changes dataset files.
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".JPG", ".JPEG")
HIGHLIGHT_COLORS = [
    np.array([218, 45, 55], dtype=np.float32),
    np.array([245, 126, 34], dtype=np.float32),
    np.array([180, 57, 185], dtype=np.float32),
]
YELLOW = np.array([255, 226, 30], dtype=np.uint8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("dataset/3dovs"),
        help="Root containing 3D-OVS scene directories.",
    )
    parser.add_argument(
        "--scenes",
        nargs="+",
        default=["bench"],
        help="Scene names under --dataset-root.",
    )
    parser.add_argument(
        "--scene-dir",
        type=Path,
        default=None,
        help="Optional direct scene/artifact-bundle directory; overrides --dataset-root/--scenes.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--topk", type=int, default=8)
    parser.add_argument(
        "--max-side",
        type=int,
        default=1400,
        help="Maximum long side for individual exported panels.",
    )
    return parser.parse_args()


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def resolve_layout(scene_dir: Path) -> Dict[str, Path]:
    bundle = scene_dir / "preprocessing"
    if (bundle / "object_mask").is_dir():
        return {
            "images": scene_dir / "rgb",
            "source": bundle / "object_mask",
            "refined": bundle / "object_mask_refined",
            "confidence": bundle / "object_confidence_ipr",
            "report": bundle / "object_mask_ipr_report" / "object_semantics.json",
        }
    return {
        "images": scene_dir / "images",
        "source": scene_dir / "object_mask",
        "refined": scene_dir / "object_mask_refined",
        "confidence": scene_dir / "object_confidence_ipr",
        "report": scene_dir / "object_mask_ipr_report" / "object_semantics.json",
    }


def find_image(images_dir: Path, stem: str) -> Path:
    for suffix in IMAGE_SUFFIXES:
        candidate = images_dir / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No RGB image for stem {stem} under {images_dir}")


def resize_long_side(image: Image.Image, max_side: int, nearest: bool = False) -> Image.Image:
    scale = min(1.0, max_side / max(image.size))
    if scale >= 1.0:
        return image
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    method = Image.Resampling.NEAREST if nearest else Image.Resampling.LANCZOS
    return image.resize(size, method)


def resize_labels(labels: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    if labels.shape == (size[1], size[0]):
        return labels
    return np.array(Image.fromarray(labels).resize(size, Image.Resampling.NEAREST))


def id_color(identity: int) -> np.ndarray:
    hue = (identity * 0.61803398875) % 1.0
    rgb = colorsys.hsv_to_rgb(hue, 0.58, 0.88)
    return np.array([round(channel * 255) for channel in rgb], dtype=np.uint8)


def colorize_ids(labels: np.ndarray) -> np.ndarray:
    canvas = np.full((*labels.shape, 3), 44, dtype=np.uint8)
    for identity in np.unique(labels):
        canvas[labels == identity] = id_color(int(identity))
    return canvas


def boundary(mask: np.ndarray) -> np.ndarray:
    inner = mask.copy()
    inner[1:-1, 1:-1] &= (
        mask[:-2, 1:-1]
        & mask[2:, 1:-1]
        & mask[1:-1, :-2]
        & mask[1:-1, 2:]
    )
    return mask & ~inner


def text_box(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], value: str, font: ImageFont.ImageFont) -> None:
    x, y = xy
    bbox = draw.textbbox((x, y), value, font=font, anchor="mm", stroke_width=1)
    pad = 8
    draw.rounded_rectangle(
        (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad),
        radius=7,
        fill=(20, 20, 20, 218),
        outline=(255, 230, 40, 255),
        width=3,
    )
    draw.text((x, y), value, font=font, anchor="mm", fill="white", stroke_width=1, stroke_fill="black")


def label_regions(image: Image.Image, labels: np.ndarray, mixed_ids: List[int]) -> Image.Image:
    result = image.convert("RGBA")
    overlay = np.array(result, dtype=np.float32)
    font = load_font(max(24, image.width // 55), bold=True)
    descriptions: List[Tuple[int, int, str]] = []
    for index, identity in enumerate(mixed_ids):
        mask = labels == identity
        if not mask.any():
            continue
        color = HIGHLIGHT_COLORS[index % len(HIGHLIGHT_COLORS)]
        overlay[mask, :3] = overlay[mask, :3] * 0.34 + color * 0.66
        overlay[boundary(mask), :3] = YELLOW
        overlay[boundary(mask), 3] = 255
        yy, xx = np.where(mask)
        ratio = float(mask.mean() * 100.0)
        descriptions.append((int(np.median(xx)), int(np.median(yy)), f"ID {identity}  large region  {ratio:.1f}%"))
    result = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8), mode="RGBA")
    draw = ImageDraw.Draw(result, "RGBA")
    for x, y, value in descriptions:
        text_box(draw, (x, y), value, font)
    return result.convert("RGB")


def label_identity_map(labels: np.ndarray, mixed_ids: List[int]) -> Image.Image:
    result = Image.fromarray(colorize_ids(labels)).convert("RGBA")
    pixels = np.array(result, dtype=np.uint8)
    for identity in mixed_ids:
        mask = labels == identity
        pixels[boundary(mask), :3] = YELLOW
        pixels[boundary(mask), 3] = 255
    result = Image.fromarray(pixels, mode="RGBA")
    draw = ImageDraw.Draw(result, "RGBA")
    font = load_font(max(24, result.width // 55), bold=True)
    for identity in mixed_ids:
        mask = labels == identity
        if not mask.any():
            continue
        yy, xx = np.where(mask)
        text_box(
            draw,
            (int(np.median(xx)), int(np.median(yy))),
            f"ID {identity}  {mask.mean() * 100.0:.1f}%",
            font,
        )
    return result.convert("RGB")


def confidence_visual(path: Path, size: Tuple[int, int]) -> Image.Image:
    if not path.is_file():
        return Image.new("RGB", size, (235, 235, 235))
    values = np.array(Image.open(path).convert("L").resize(size, Image.Resampling.NEAREST), dtype=np.float32) / 255.0
    dark = np.array([62, 71, 73], dtype=np.float32)
    bright = np.array([255, 222, 90], dtype=np.float32)
    rgb = dark[None, None, :] * (1.0 - values[..., None]) + bright[None, None, :] * values[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def panel_with_header(image: Image.Image, title: str, width: int, height: int) -> Image.Image:
    header = 64
    canvas = Image.new("RGB", (width, height + header), "white")
    fitted = image.copy()
    fitted.thumbnail((width, height), Image.Resampling.LANCZOS)
    x = (width - fitted.width) // 2
    y = header + (height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.text((width // 2, header // 2), title, font=load_font(30, bold=True), anchor="mm", fill=(25, 25, 25))
    return canvas


def make_contact_sheet(
    rgb: Image.Image,
    identity: Image.Image,
    highlighted: Image.Image,
    confidence: Image.Image,
    mixed_ids: List[int],
) -> Image.Image:
    panel_w, panel_h, gap = 700, 525, 18
    panels = [
        panel_with_header(rgb, "RGB", panel_w, panel_h),
        panel_with_header(identity, "Identity IDs", panel_w, panel_h),
        panel_with_header(highlighted, "Flagged large-region IDs", panel_w, panel_h),
        panel_with_header(confidence, "IPR confidence", panel_w, panel_h),
    ]
    footer = 82
    canvas = Image.new("RGB", (panel_w * 4 + gap * 3, panels[0].height + footer), (246, 247, 248))
    for index, panel in enumerate(panels):
        canvas.paste(panel, (index * (panel_w + gap), 0))
    draw = ImageDraw.Draw(canvas)
    message = (
        "Yellow boundaries and red/orange overlays mark IDs flagged as large_mixed_region: "
        + ", ".join(str(identity) for identity in mixed_ids)
    )
    draw.text((canvas.width // 2, panels[0].height + footer // 2), message,
              font=load_font(27, bold=True), anchor="mm", fill=(35, 35, 35))
    return canvas


def rank_frames(layout: Dict[str, Path], mixed_ids: List[int]) -> List[Tuple[float, str, Dict[int, float]]]:
    rows: List[Tuple[float, str, Dict[int, float]]] = []
    for mask_path in sorted(layout["refined"].glob("*.png")):
        labels = np.array(Image.open(mask_path))
        ratios = {identity: float(np.mean(labels == identity)) for identity in mixed_ids}
        present = [ratio for ratio in ratios.values() if ratio > 0]
        if not present:
            continue
        # Prefer frames where multiple problematic regions are simultaneously large and visible.
        balance = min(present) if len(present) > 1 else 0.0
        score = sum(present) + 0.75 * balance
        rows.append((score, mask_path.stem, ratios))
    return sorted(rows, reverse=True)


def export_scene(scene_name: str, scene_dir: Path, output: Path, topk: int, max_side: int) -> None:
    layout = resolve_layout(scene_dir)
    for key, path in layout.items():
        if key != "confidence" and not path.exists():
            raise FileNotFoundError(f"Missing {key}: {path}")
    report = json.loads(layout["report"].read_text(encoding="utf-8"))
    mixed_ids = sorted(
        int(identity)
        for identity, record in report["object_weights"].items()
        if record.get("reason") == "large_mixed_region"
    )
    if not mixed_ids:
        raise RuntimeError(f"{scene_name}: no large_mixed_region identities in {layout['report']}")

    scene_out = output / scene_name
    candidates_out = scene_out / "candidates"
    best_out = scene_out / "best"
    candidates_out.mkdir(parents=True, exist_ok=True)
    best_out.mkdir(parents=True, exist_ok=True)

    ranked = rank_frames(layout, mixed_ids)
    if not ranked:
        raise RuntimeError(f"{scene_name}: no matching mask frames")

    csv_rows = []
    for rank, (score, stem, ratios) in enumerate(ranked[:topk], start=1):
        rgb = Image.open(find_image(layout["images"], stem)).convert("RGB")
        labels = np.array(Image.open(layout["refined"] / f"{stem}.png"))
        labels = resize_labels(labels, rgb.size)
        rgb = resize_long_side(rgb, max_side)
        labels = resize_labels(labels, rgb.size)
        identity = label_identity_map(labels, mixed_ids)
        highlighted = label_regions(rgb, labels, mixed_ids)
        confidence = confidence_visual(layout["confidence"] / f"{stem}.png", rgb.size)
        sheet = make_contact_sheet(rgb, identity, highlighted, confidence, mixed_ids)
        sheet_path = candidates_out / f"rank_{rank:02d}_{stem}.png"
        sheet.save(sheet_path, optimize=True)
        csv_rows.append({
            "rank": rank,
            "frame": stem,
            "score": score,
            "mixed_ids": " ".join(str(value) for value in mixed_ids),
            "ratios": json.dumps({str(key): value for key, value in ratios.items()}),
            "contact_sheet": str(sheet_path),
        })
        if rank == 1:
            rgb.save(best_out / "rgb.png", optimize=True)
            identity.save(best_out / "identity_ids_labeled.png", optimize=True)
            highlighted.save(best_out / "large_region_highlight.png", optimize=True)
            confidence.save(best_out / "ipr_confidence.png", optimize=True)
            sheet.save(best_out / "best_contact_sheet.png", optimize=True)
            (best_out / "manifest.json").write_text(
                json.dumps(
                    {
                        "scene": scene_name,
                        "frame": stem,
                        "mixed_ids": mixed_ids,
                        "area_ratios": {str(key): value for key, value in ratios.items()},
                        "score": score,
                        "source_scene": str(scene_dir),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    with (scene_out / "candidate_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[{scene_name}] mixed IDs: {mixed_ids}")
    print(f"[{scene_name}] best frame: {ranked[0][1]}")
    print(f"[{scene_name}] output: {scene_out}")


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.scene_dir is not None:
        export_scene(args.scene_dir.name, args.scene_dir, args.output, args.topk, args.max_side)
        return
    completed = 0
    for scene in args.scenes:
        try:
            export_scene(scene, args.dataset_root / scene, args.output, args.topk, args.max_side)
            completed += 1
        except (FileNotFoundError, KeyError, RuntimeError, json.JSONDecodeError) as error:
            print(f"[{scene}] skipped: {error}")
    if completed == 0:
        raise RuntimeError("No scene produced a usable large-region example.")
    print(f"Completed {completed}/{len(args.scenes)} scenes.")


if __name__ == "__main__":
    main()
