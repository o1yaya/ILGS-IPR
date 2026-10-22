#!/usr/bin/env python3
"""Build self-contained editable SVG method and pipeline figures from real exports."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import subprocess
from html import escape
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


PALETTE = np.array(
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

BLACK = "#222222"
MUTED = "#52636D"
BLUE = "#2166AC"
GREEN = "#1B7837"
ORANGE = "#E67E22"
RED = "#B2182B"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def save_png(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, optimize=True)
    return path


def colorize_labels(array: np.ndarray) -> Image.Image:
    labels = np.asarray(array, dtype=np.int64)
    return Image.fromarray(PALETTE[labels % len(PALETTE)], "RGB")


def reliability_color(path: Path) -> Image.Image:
    values = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    low = np.array([61, 74, 82], dtype=np.float32)
    mid = np.array([241, 163, 64], dtype=np.float32)
    high = np.array([255, 239, 138], dtype=np.float32)
    first = np.minimum(values * 2.0, 1.0)[..., None]
    second = np.maximum(values * 2.0 - 1.0, 0.0)[..., None]
    rgb = low * (1.0 - first) + mid * first
    rgb = rgb * (1.0 - second) + high * second
    return Image.fromarray(np.uint8(np.clip(rgb, 0, 255)), "RGB")


def normalize_feature(path: Path) -> Image.Image:
    values = np.load(path)
    if values.ndim != 3:
        raise ValueError(f"Expected CHW/HWC feature tensor: {path} {values.shape}")
    if values.shape[0] in (1, 2, 3, 4):
        values = np.moveaxis(values[:3], 0, -1)
    if values.shape[-1] == 1:
        values = np.repeat(values, 3, axis=-1)
    channels = []
    for index in range(3):
        channel = values[..., index].astype(np.float32)
        finite = channel[np.isfinite(channel)]
        low, high = np.percentile(finite, [2, 98]) if finite.size else (0.0, 1.0)
        if high <= low:
            high = low + 1.0
        channels.append(np.clip((channel - low) / (high - low), 0.0, 1.0))
    rgb = np.stack(channels, axis=-1)
    return Image.fromarray(np.uint8(rgb * 255.0), "RGB")


def label_argmax(path: Path) -> Image.Image:
    values = np.load(path)
    if values.ndim == 3:
        axis = 0 if values.shape[0] < values.shape[-1] else -1
        values = values.argmax(axis=axis)
    return colorize_labels(values)


def fit(image: Image.Image, size: tuple[int, int], crop: bool = True) -> Image.Image:
    image = image.convert("RGB")
    if crop:
        return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return canvas


def structure_cleanup(raw_path: Path, clean_path: Path, size=(900, 420)) -> Image.Image:
    raw = np.asarray(Image.open(raw_path))
    clean = np.asarray(Image.open(clean_path))
    changed = raw != clean
    yy, xx = np.where(changed)
    if len(xx) == 0:
        x0, y0, x1, y1 = 0, 0, raw.shape[1], raw.shape[0]
    else:
        width = max(80, int(xx.max() - xx.min() + 1))
        height = max(80, int(yy.max() - yy.min() + 1))
        side = max(width, height) * 6
        cx, cy = int((xx.min() + xx.max()) / 2), int((yy.min() + yy.max()) / 2)
        x0, x1 = max(0, cx - side // 2), min(raw.shape[1], cx + side // 2)
        y0, y1 = max(0, cy - side // 2), min(raw.shape[0], cy + side // 2)
    before = colorize_labels(raw[y0:y1, x0:x1])
    after = colorize_labels(clean[y0:y1, x0:x1])
    gap = 10
    tile_w = (size[0] - gap) // 2
    canvas = Image.new("RGB", size, "white")
    canvas.paste(fit(before, (tile_w, size[1])), (0, 0))
    canvas.paste(fit(after, (tile_w, size[1])), (tile_w + gap, 0))
    return canvas


def crop_id_consistency(frame_dirs: list[Path], identity: int, size=(900, 420)) -> Image.Image:
    gap = 12
    tile_w = (size[0] - gap * 2) // 3
    canvas = Image.new("RGB", size, "white")
    for index, frame_dir in enumerate(frame_dirs):
        labels = np.asarray(Image.open(frame_dir / "cleaned_identity_labels.png"))
        mask = labels == identity
        yy, xx = np.where(mask)
        rgb = Image.open(frame_dir / "rgb.jpg").convert("RGB")
        if len(xx) == 0:
            crop = rgb
        else:
            pad = max(30, int(max(xx.max() - xx.min(), yy.max() - yy.min()) * 0.14))
            box = (
                max(0, int(xx.min()) - pad),
                max(0, int(yy.min()) - pad),
                min(labels.shape[1], int(xx.max()) + pad + 1),
                min(labels.shape[0], int(yy.max()) + pad + 1),
            )
            crop = rgb.crop(box)
            local_mask = Image.fromarray(np.uint8(mask[box[1]:box[3], box[0]:box[2]]) * 255)
            muted = ImageOps.grayscale(crop).convert("RGB").point(lambda value: int(value * 0.7))
            crop = Image.composite(crop, muted, local_mask)
        canvas.paste(fit(crop, (tile_w, size[1])), (index * (tile_w + gap), 0))
    return canvas


def large_region_risk(labels_path: Path, large_ids: list[int]) -> Image.Image:
    labels = np.asarray(Image.open(labels_path))
    rgb = np.full((*labels.shape, 3), [224, 229, 231], dtype=np.uint8)
    risk = np.isin(labels, large_ids)
    rgb[risk] = np.array([241, 163, 64], dtype=np.uint8)
    boundary = Image.fromarray(np.uint8(risk) * 255).filter(ImageFilter.MaxFilter(13))
    edge = np.asarray(boundary) > 0
    rgb[np.logical_and(edge, ~risk)] = np.array([178, 24, 43], dtype=np.uint8)
    return Image.fromarray(rgb, "RGB")


def mask_overlay(rgb_path: Path, mask_path: Path, color: tuple[int, int, int]) -> Image.Image:
    mask = Image.open(mask_path).convert("L")
    rgb = fit(Image.open(rgb_path), mask.size)
    grey = ImageOps.grayscale(rgb).convert("RGB")
    mask_array = np.asarray(mask) >= 128
    base = np.asarray(grey).astype(np.float32)
    tint = np.zeros_like(base)
    tint[:] = color
    base[mask_array] = base[mask_array] * 0.28 + tint[mask_array] * 0.72
    binary = Image.fromarray(np.uint8(mask_array) * 255)
    expanded = np.asarray(binary.filter(ImageFilter.MaxFilter(11))) > 0
    contracted = np.asarray(binary.filter(ImageFilter.MinFilter(11))) > 0
    edge = expanded != contracted
    base[edge] = np.array([255, 224, 79], dtype=np.float32)
    return Image.fromarray(np.uint8(np.clip(base, 0, 255)), "RGB")


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def svg_text(x, y, value, size=24, weight=400, color=BLACK, anchor="middle", italic=False, extra=""):
    style = "italic" if italic else "normal"
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
        f'text-anchor="{anchor}" fill="{color}" letter-spacing="0" {extra}>{escape(value)}</text>'
    )


def svg_multiline(x, y, lines, size=24, weight=400, color=BLACK, anchor="middle", line_height=1.18):
    spans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else size * line_height
        spans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{color}" letter-spacing="0">{"".join(spans)}</text>'
    )


def svg_image(path: Path, x, y, width, height, image_id: str):
    return (
        f'<image id="{image_id}" x="{x}" y="{y}" width="{width}" height="{height}" '
        f'preserveAspectRatio="none" href="{data_uri(path)}" />'
    )


def arrow(x1, y1, x2, y2, color=BLACK, width=3, marker="arrow-black", dash=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
        f'stroke-width="{width}" marker-end="url(#{marker})"{dash_attr}/>'
    )


def poly_arrow(points, color=BLACK, width=3, marker="arrow-black"):
    coords = " ".join(f"{x},{y}" for x, y in points)
    return (
        f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round" marker-end="url(#{marker})"/>'
    )


def rounded_rect(x, y, width, height, fill, radius=8, stroke="none", stroke_width=0):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def title(panel, letter, name, x, y, accent=BLACK):
    panel.append(svg_text(x, y, letter, size=38, weight=700, anchor="start", color=accent))
    panel.append(svg_text(x + 48, y, name, size=34, weight=700, anchor="start"))


def svg_defs():
    return """
    <defs>
      <marker id="arrow-black" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#222222"/></marker>
      <marker id="arrow-orange" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#E67E22"/></marker>
      <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#2166AC"/></marker>
      <marker id="arrow-red" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#B2182B"/></marker>
    </defs>
    """


def prepare_scene(root: Path, scene: str, train_stems: list[str], test_stem: str, query: str, view: int, out: Path):
    scene_root = root / scene
    frame_dirs = [scene_root / "training_frames" / stem for stem in train_stems]
    primary = frame_dirs[0]
    cleanup_frame = max(
        frame_dirs,
        key=lambda frame: np.count_nonzero(
            np.asarray(Image.open(frame / "noisy_identity_labels.png"))
            != np.asarray(Image.open(frame / "cleaned_identity_labels.png"))
        ),
    )
    report_path = scene_root / "dataset" / "object_mask_ipr_trainview_consistency_strict_report" / "object_semantics.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    large_ids = [int(key) for key, value in report["object_weights"].items() if value["reason"] == "large_mixed_region"]
    trusted_ids = [int(key) for key, value in report["object_weights"].items() if value["reason"] == "trusted"]
    identity = max(
        trusted_ids,
        key=lambda value: min(
            np.count_nonzero(np.asarray(Image.open(frame / "cleaned_identity_labels.png")) == value)
            for frame in frame_dirs
        ),
    )

    model_frame = scene_root / "models" / "ipr" / "test" / "frames" / test_stem
    rgb_test = scene_root / "dataset" / "images" / f"{test_stem}.jpg"
    official_mask = scene_root / "models" / "official" / "test" / "test_mask" / str(view) / f"{query}.png"
    ipr_mask = scene_root / "models" / "ipr" / "test" / "test_mask" / str(view) / f"{query}.png"

    prepared = {
        "rgb_train": save_png(fit(Image.open(primary / "rgb.jpg"), (900, 675)), out / f"{scene}_rgb_train.png"),
        "raw_labels": save_png(fit(colorize_labels(np.asarray(Image.open(primary / "noisy_identity_labels.png"))), (900, 675)), out / f"{scene}_raw_labels.png"),
        "clean_labels": save_png(fit(colorize_labels(np.asarray(Image.open(primary / "cleaned_identity_labels.png"))), (900, 675)), out / f"{scene}_clean_labels.png"),
        "reliability": save_png(fit(reliability_color(primary / "reliability_map.png"), (900, 675)), out / f"{scene}_reliability.png"),
        "cleanup_zoom": save_png(structure_cleanup(cleanup_frame / "noisy_identity_labels.png", cleanup_frame / "cleaned_identity_labels.png"), out / f"{scene}_cleanup_zoom.png"),
        "crop_consistency": save_png(crop_id_consistency(frame_dirs, identity), out / f"{scene}_crop_consistency.png"),
        "large_risk": save_png(fit(large_region_risk(primary / "cleaned_identity_labels.png", large_ids), (900, 675)), out / f"{scene}_large_risk.png"),
        "render_rgb": save_png(fit(Image.open(model_frame / "render_rgb.png"), (900, 675)), out / f"{scene}_render_rgb.png"),
        "identity_feature": save_png(fit(Image.open(model_frame / "identity_feature.png"), (900, 675)), out / f"{scene}_identity_feature.png"),
        "identity_logits": save_png(fit(label_argmax(model_frame / "identity_logits.npy"), (900, 675)), out / f"{scene}_identity_logits.png"),
        "language_feature": save_png(fit(normalize_feature(model_frame / "language_feature.npy"), (900, 675)), out / f"{scene}_language_feature.png"),
        "rgb_test": save_png(fit(Image.open(rgb_test), (900, 675)), out / f"{scene}_rgb_test.png"),
        "official_overlay": save_png(fit(mask_overlay(rgb_test, official_mask, (178, 24, 43)), (900, 675)), out / f"{scene}_official_overlay.png"),
        "ipr_overlay": save_png(fit(mask_overlay(rgb_test, ipr_mask, (27, 120, 55)), (900, 675)), out / f"{scene}_ipr_overlay.png"),
        "ipr_mask": save_png(fit(Image.open(ipr_mask).convert("RGB"), (900, 675)), out / f"{scene}_ipr_mask.png"),
    }
    provenance = {
        "scene": scene,
        "training_frames": train_stems,
        "primary_training_frame": primary.name,
        "cleanup_zoom_frame": cleanup_frame.name,
        "same_id_crop_identity": identity,
        "large_mixed_region_ids": large_ids,
        "test_frame": test_stem,
        "query": query,
        "evaluation_view_index": view,
        "manual_mask_editing": False,
        "feature_display_transform": "Per-channel 2nd-to-98th percentile normalization of the exported 3-channel tensor.",
        "prediction_display_transform": "Unedited binary prediction over grayscale source RGB; deterministic colored fill and outline added for visibility.",
        "sources": {
            "training_rgb": str(primary / "rgb.jpg"),
            "raw_labels": str(primary / "noisy_identity_labels.png"),
            "clean_labels": str(primary / "cleaned_identity_labels.png"),
            "reliability": str(primary / "reliability_map.png"),
            "object_report": str(report_path),
            "render_rgb": str(model_frame / "render_rgb.png"),
            "identity_feature": str(model_frame / "identity_feature.png"),
            "identity_logits": str(model_frame / "identity_logits.npy"),
            "language_feature": str(model_frame / "language_feature.npy"),
            "official_mask": str(official_mask),
            "ipr_mask": str(ipr_mask),
            "test_rgb": str(rgb_test),
        },
    }
    return prepared, provenance


def build_pipeline(asset, output: Path):
    W, H = 2200, 1020
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="183mm" height="84.85mm" viewBox="0 0 {W} {H}">']
    svg.append('<title>Real-data ILGS-IPR training pipeline</title>')
    svg.append('<desc>All raster panels are derived from unedited strict_trainview_consistency exports for the 3D-OVS Covered Desk scene. Text, arrows, boxes and the outlier gate are editable vectors.</desc>')
    svg.append(svg_defs())
    svg.append('<rect width="2200" height="1020" fill="#FFFFFF"/>')

    panels = [
        (20, 20, 310, 980, "#F2F5F8"),
        (345, 20, 670, 980, "#FFF7EA"),
        (1030, 20, 410, 980, "#F4F2F8"),
        (1455, 20, 725, 980, "#EEF7F1"),
    ]
    for box in panels:
        svg.append(rounded_rect(*box))

    # a. Inputs
    svg.append(svg_text(42, 72, "a", size=38, weight=700, anchor="start"))
    svg.append(svg_text(85, 72, "Input supervision", size=27, weight=700, anchor="start"))
    svg.append(svg_image(asset["rgb_train"], 45, 125, 260, 195, "pipeline-input-rgb"))
    svg.append(svg_text(175, 354, "RGB training view", 23))
    svg.append(svg_image(asset["raw_labels"], 45, 425, 260, 195, "pipeline-input-labels"))
    svg.append(svg_text(175, 654, "Noisy identity labels", 23))
    svg.append(rounded_rect(70, 760, 210, 88, "#FFFFFF", radius=8))
    svg.append(svg_multiline(175, 793, ["Training views", "only"], size=21, weight=700, color=MUTED))

    # b. IPR
    title(svg, "b", "Identity-preserving reliability", 367, 72, ORANGE)
    top_x = [375, 588, 801]
    labels = ["Sparse cleanup", "Same-ID consistency", "Large-region risk"]
    keys = ["cleanup_zoom", "crop_consistency", "large_risk"]
    for x, label, key in zip(top_x, labels, keys):
        svg.append(svg_text(x + 92, 127, label, 20, 700))
        svg.append(svg_image(asset[key], x, 150, 184, 135, f"pipeline-{key}"))
        svg.append(poly_arrow([(x + 92, 290), (x + 92, 344), (680, 344), (680, 370)], ORANGE, 2.5, "arrow-orange"))
    svg.append(rounded_rect(455, 370, 450, 78, "#FFE8C4", radius=8))
    svg.append(svg_text(680, 420, "Pixel reliability estimation", 27, 700))
    svg.append(arrow(680, 448, 680, 506, BLUE, 3, "arrow-blue"))
    svg.append(svg_image(asset["clean_labels"], 400, 530, 260, 195, "pipeline-clean-labels"))
    svg.append(svg_text(530, 758, "Cleaned labels  Y'", 23, 700, GREEN))
    svg.append(svg_image(asset["reliability"], 700, 530, 260, 195, "pipeline-reliability"))
    svg.append(svg_text(830, 758, "Reliability  W(p)", 23, 700, BLUE))
    svg.append(svg_multiline(680, 865, ["Preserve identity anchors;", "downweight unreliable pixels"], 22, 400, MUTED))

    # c. Field
    title(svg, "c", "Gaussian field", 1052, 72)
    svg.append(svg_image(asset["render_rgb"], 1055, 125, 360, 270, "pipeline-field-rgb"))
    svg.append(svg_multiline(1235, 430, ["Identity-aware", "language Gaussians"], 23, 700))
    svg.append(svg_image(asset["language_feature"], 1055, 510, 170, 128, "pipeline-field-language"))
    svg.append(svg_image(asset["identity_feature"], 1245, 510, 170, 128, "pipeline-field-identity"))
    svg.append(svg_text(1140, 670, "Language", 20, 700))
    svg.append(svg_text(1330, 670, "Identity", 20, 700))
    svg.append(rounded_rect(1100, 750, 270, 150, "#FFFFFF", radius=8))
    for index, (name, color) in enumerate([("Appearance", "#F2F2F2"), ("Language", "#E8F2FA"), ("Identity", "#FFF0D0")]):
        svg.append(f'<rect x="1100" y="{750 + index * 50}" width="270" height="50" fill="{color}"/>')
        svg.append(svg_text(1235, 783 + index * 50, name, 20, 700))

    # d. Optimization
    title(svg, "d", "Joint optimization", 1477, 72, GREEN)
    svg.append(svg_text(1818, 104, "Representative tensors; objectives shown schematically", 15, 400, MUTED))
    left_x, box_x, right_x = 1485, 1714, 1980
    image_w, image_h = 190, 142
    rows = [(165, "Identity", "identity_logits", "clean_labels"), (445, "Language", "language_feature", None), (725, "RGB", "render_rgb", "rgb_test")]
    for y, branch, left_key, right_key in rows:
        svg.append(svg_image(asset[left_key], left_x, y, image_w, image_h, f"pipeline-{branch.lower()}-render"))
        svg.append(svg_text(left_x + image_w / 2, y + 177, f"Rasterized {branch.lower()}", 20))
        svg.append(rounded_rect(box_x, y + 26, 210, 90, "#FFFFFF", radius=8))
        svg.append(svg_multiline(box_x + 105, y + 63, [f"{branch}", "loss"], 23, 700))
        svg.append(arrow(left_x + image_w, y + 71, box_x - 10, y + 71, RED, 2.5, "arrow-red"))
        if right_key:
            svg.append(svg_image(asset[right_key], right_x, y, 170, image_h, f"pipeline-{branch.lower()}-target"))
            target_label = "Cleaned labels" if branch == "Identity" else "Ground-truth RGB"
            svg.append(svg_text(right_x + 85, y + 177, target_label, 20))
        else:
            svg.append(rounded_rect(right_x, y, 170, image_h, "#FFFFFF", radius=8))
            svg.append(svg_multiline(right_x + 85, y + 60, ["2D CLIP", "feature map"], 21, 700, BLUE))
        svg.append(arrow(right_x - 10, y + 71, box_x + 220, y + 71, RED, 2.5, "arrow-red"))

    svg.append(rounded_rect(1754, 105, 130, 50, "#FFFFFF", radius=8))
    svg.append(svg_text(1819, 138, "outlier gate  o(p)", 16, 700, MUTED))
    svg.append(arrow(1819, 155, 1819, 184, BLACK, 2, "arrow-black"))
    svg.append(svg_text(1819, 342, "W(p)", 27, 700, BLUE))
    svg.append(arrow(1819, 330, 1819, 294, BLUE, 2.5, "arrow-blue"))
    svg.append(svg_text(1819, 963, "Only the 2D identity branch is reweighted", 21, 700, GREEN))

    # Cross-panel flow
    svg.append(arrow(305, 220, 365, 220, BLACK, 3, "arrow-black"))
    svg.append(poly_arrow([(305, 522), (330, 522), (330, 270), (365, 270)], BLACK, 3, "arrow-black"))
    svg.append(arrow(1015, 510, 1045, 510, BLACK, 3, "arrow-black"))
    svg.append(poly_arrow([(1370, 825), (1445, 825), (1445, 236), (1475, 236)], BLACK, 3, "arrow-black"))

    svg.append('</svg>')
    output.write_text("\n".join(svg), encoding="utf-8")


def fraction_formula(x, y, width=560):
    parts = []
    parts.append('<g id="editable-weighted-loss-formula" inkscape:label="Editable weighted identity loss">')
    parts.append(
        f'<text x="{x}" y="{y + 22}" font-family="Times New Roman, Times, serif" font-size="34" '
        f'font-style="italic" fill="{BLACK}">L'
        f'<tspan baseline-shift="sub" font-size="19">id</tspan>'
        f'<tspan baseline-shift="super" font-size="17">IPR</tspan></text>'
    )
    parts.append(svg_text(x + 70, y + 22, "=", 32, 400, BLACK, "start"))
    line_x1, line_x2 = x + 112, x + width
    cx = (line_x1 + line_x2) / 2
    parts.append(
        f'<text x="{cx}" y="{y - 4}" font-family="Times New Roman, Times, serif" font-size="23" '
        f'font-style="italic" text-anchor="middle" fill="{BLACK}">Σ'
        f'<tspan baseline-shift="sub" font-size="15">p</tspan>'
        f'<tspan baseline-shift="baseline"> o(p) W(p) ℓ</tspan>'
        f'<tspan baseline-shift="sub" font-size="15">id</tspan>'
        f'<tspan baseline-shift="baseline">(p)</tspan></text>'
    )
    parts.append(f'<line x1="{line_x1}" y1="{y + 10}" x2="{line_x2}" y2="{y + 10}" stroke="{BLACK}" stroke-width="2"/>')
    parts.append(
        f'<text x="{cx}" y="{y + 43}" font-family="Times New Roman, Times, serif" font-size="20" '
        f'font-style="italic" text-anchor="middle" fill="{BLACK}">max(Σ'
        f'<tspan baseline-shift="sub" font-size="14">p</tspan>'
        f'<tspan baseline-shift="baseline"> o(p) W(p), 1) log C</tspan></text>'
    )
    parts.append('</g>')
    return "".join(parts)


def build_method(asset, output: Path):
    W, H = 2200, 1450
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="183mm" height="120.6mm" viewBox="0 0 {W} {H}">']
    svg.append('<title>Real-data IPR method figure</title>')
    svg.append('<desc>All raster panels are derived from unedited strict_trainview_consistency exports for the 3D-OVS Bench scene. The formula, labels and arrows remain editable vectors.</desc>')
    svg.append(svg_defs())
    svg.append('<rect width="2200" height="1450" fill="#FFFFFF"/>')
    svg.append(rounded_rect(20, 20, 2160, 490, "#F1F6F8"))
    svg.append(rounded_rect(20, 530, 450, 900, "#F2F5F8"))
    svg.append(rounded_rect(490, 530, 1050, 900, "#FFF7EA"))
    svg.append(rounded_rect(1560, 530, 620, 900, "#EEF7F1"))

    # c. Field band
    title(svg, "c", "Confidence-weighted identity-aware Gaussian field", 45, 72, GREEN)
    keys = ["render_rgb", "language_feature", "identity_feature", "ipr_mask"]
    labels = ["Novel view", "Language feature", "Identity feature", "Query segmentation"]
    xs = [55, 580, 1105, 1630]
    for index, (x, key, label) in enumerate(zip(xs, keys, labels)):
        svg.append(svg_text(x + 235, 127, label, 24, 700))
        svg.append(svg_image(asset[key], x, 150, 470, 300, f"method-field-{index}"))
    svg.append(svg_text(1865, 485, 'Text query: "Portuguese egg tart"', 22, 700))

    # a. Raw supervision
    title(svg, "a", "Noisy identity labels", 43, 582, RED)
    svg.append(svg_image(asset["rgb_train"], 50, 635, 390, 292, "method-input-rgb"))
    svg.append(svg_text(245, 958, "RGB training view", 23))
    svg.append(svg_image(asset["raw_labels"], 50, 1010, 390, 292, "method-input-labels"))
    svg.append(svg_text(245, 1337, "Raw identity supervision", 23, 700))
    svg.append(svg_text(245, 1382, "Large mixed IDs dominate many pixels", 20, 400, MUTED))

    # b. IPR
    title(svg, "b", "IPR: estimate pixel reliability", 513, 582, ORANGE)
    top_x = [520, 860, 1200]
    top_labels = ["Sparse cleanup", "Same-ID crop consistency", "Large-region risk"]
    top_keys = ["cleanup_zoom", "crop_consistency", "large_risk"]
    for x, label, key in zip(top_x, top_labels, top_keys):
        svg.append(svg_text(x + 155, 635, label, 20, 700))
        svg.append(svg_image(asset[key], x, 660, 310, 190, f"method-{key}"))
        svg.append(poly_arrow([(x + 155, 850), (x + 155, 905), (875, 905), (875, 930)], ORANGE, 2.5, "arrow-orange"))
    svg.append(svg_image(asset["reliability"], 565, 955, 460, 345, "method-reliability"))
    svg.append(svg_text(795, 1335, "Reliability map  W(p)", 24, 700, BLUE))
    svg.append(rounded_rect(1045, 1000, 450, 205, "#FFF0D9", radius=8))
    svg.append(svg_text(1270, 1040, "Confidence-weighted identity loss", 20, 700, ORANGE))
    svg.append(fraction_formula(1075, 1105, 390))
    svg.append(arrow(1025, 1128, 1035, 1128, BLUE, 3, "arrow-blue"))
    svg.append(svg_multiline(1278, 1282, ["Sparse label repair; dense confidence", "reweights unreliable supervision"], 20, 400, MUTED))

    # d. Real output comparison
    title(svg, "d", "Cleaner segment", 1583, 582, GREEN)
    svg.append(svg_text(1870, 636, 'Text query: "Portuguese egg tart"', 21, 700))
    svg.append(svg_text(1870, 681, "Official ILGS", 23, 700, RED))
    svg.append(svg_image(asset["official_overlay"], 1600, 705, 540, 330, "method-official-output"))
    svg.append(arrow(1870, 1040, 1870, 1080, GREEN, 3, "arrow-black"))
    svg.append(svg_text(1870, 1118, "ILGS + IPR", 23, 700, GREEN))
    svg.append(svg_image(asset["ipr_overlay"], 1600, 1140, 540, 230, "method-ipr-output"))
    svg.append(svg_text(1870, 1402, "Raw predictions; no pixel editing", 19, 400, MUTED))

    # Flow arrows
    svg.append(arrow(440, 1115, 510, 1115, BLACK, 3, "arrow-black"))
    svg.append(poly_arrow([(1495, 1128), (1535, 1128), (1535, 355), (1615, 355)], BLUE, 3, "arrow-blue"))
    svg.append(arrow(1870, 510, 1870, 550, BLACK, 2.5, "arrow-black"))

    svg.append('</svg>')
    output.write_text("\n".join(svg), encoding="utf-8")


def export_with_inkscape(inkscape: Path, svg: Path):
    png = svg.with_suffix(".png")
    pdf = svg.with_suffix(".pdf")
    subprocess.run([str(inkscape), str(svg), "--export-type=png", f"--export-filename={png}", "--export-dpi=300", "--export-area-page"], check=True)
    subprocess.run([str(inkscape), str(svg), "--export-type=pdf", f"--export-filename={pdf}", "--export-area-page"], check=True)
    return png, pdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("asset_root", type=Path)
    parser.add_argument("figure_dir", type=Path)
    parser.add_argument("--inkscape", type=Path, default=Path("E:/Inkscape/bin/inkscape.com"))
    args = parser.parse_args()

    audit_path = Path("outputs/real_main_figure_rebuild_20261018/audit/real_asset_audit.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    prepared_dir = args.figure_dir / "current_ipr_real_assets"
    prepared_dir.mkdir(parents=True, exist_ok=True)

    bench_selected = audit["scenes"]["bench"]["query_evaluation"]["selected"]
    covered_selected = audit["scenes"]["covered_desk"]["query_evaluation"]["selected"]
    bench_frame_names = json.loads((args.asset_root / "bench/models/ipr/test/frame_names.json").read_text())
    covered_frame_names = json.loads((args.asset_root / "covered_desk/models/ipr/test/frame_names.json").read_text())

    bench, bench_provenance = prepare_scene(
        args.asset_root,
        "bench",
        [item["stem"] for item in audit["scenes"]["bench"]["training_frames"]],
        bench_frame_names[f"{bench_selected['view']:05d}"],
        bench_selected["query"],
        bench_selected["view"],
        prepared_dir,
    )
    covered, covered_provenance = prepare_scene(
        args.asset_root,
        "covered_desk",
        [item["stem"] for item in audit["scenes"]["covered_desk"]["training_frames"]],
        covered_frame_names[f"{covered_selected['view']:05d}"],
        covered_selected["query"],
        covered_selected["view"],
        prepared_dir,
    )

    pipeline_svg = args.figure_dir / "pipeline_final_current_ipr.svg"
    method_svg = args.figure_dir / "method_final_current_ipr.svg"
    build_pipeline(covered, pipeline_svg)
    build_method(bench, method_svg)
    pipeline_png, pipeline_pdf = export_with_inkscape(args.inkscape, pipeline_svg)
    method_png, method_pdf = export_with_inkscape(args.inkscape, method_svg)

    provenance = {
        "protocol": audit["protocol"],
        "seed": audit["seed"],
        "manual_mask_editing": False,
        "pipeline": {
            "scene": "covered_desk",
            "provenance": covered_provenance,
            "svg": str(pipeline_svg),
            "png": str(pipeline_png),
            "pdf": str(pipeline_pdf),
        },
        "method": {
            "scene": "bench",
            "selection_rule": "Query with highest mean Official-to-IPR IoU change across all exported test views; representative positive view closest to that query's mean change.",
            "provenance": bench_provenance,
            "svg": str(method_svg),
            "png": str(method_png),
            "pdf": str(method_pdf),
        },
        "display_only_elements": [
            "panel backgrounds, arrows, labels and loss boxes",
            "dynamic outlier gate o(p), because it is computed online and is not stored as an image",
            "deterministic label palettes, feature normalization, and colored prediction overlays",
        ],
        "output_hashes": {
            path.name: sha256(path)
            for path in [pipeline_svg, pipeline_png, pipeline_pdf, method_svg, method_png, method_pdf]
        },
    }
    provenance_path = args.figure_dir / "real_main_figures_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"pipeline": str(pipeline_svg), "method": str(method_svg), "provenance": str(provenance_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
