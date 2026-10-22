# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# Custom contribution-oriented layout using only real exported artifacts and deterministic overlays.
from pathlib import Path
import json

import matplotlib as mpl

mpl.use("Agg")
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666", "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999"]
DIVERGING = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED = "#B2182B"
GREY = "#999999"
BLACK = "#222222"
mpl.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none", "savefig.bbox": "tight", "savefig.dpi": 300})

import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ASSET = Path(r"D:\downloads\ipr_method_assets\bench_20261007_203512_313407")
RGB_ROOT = ROOT / "dataset" / "3dovs" / "bench" / "images"
OUT = ROOT / "outputs" / "method_figure_contribution_20261008"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 183.0, 121.0
fig = plt.figure(figsize=(W / 25.4, H / 25.4), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set(xlim=(0, W), ylim=(H, 0))
ax.axis("off")

INK = "#222222"
RED = "#B2182B"
GREEN = "#177560"
BLUE = "#315A89"
YELLOW = "#E9D52D"
PANEL = "#E6EBF5"


def text(x, y, value, size=7, bold=False, ha="left", color=INK):
    return ax.text(
        x,
        y,
        value,
        fontsize=size,
        weight="bold" if bold else "normal",
        ha=ha,
        va="center",
        color=color,
        linespacing=1.1,
        zorder=30,
    )


def image_tile(image_or_path, x, y, w, h, edge="#FFFFFF", lw=0.7):
    image = image_or_path if isinstance(image_or_path, Image.Image) else Image.open(image_or_path)
    tile = fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H], zorder=6)
    tile.imshow(image)
    tile.set_aspect("auto")
    tile.set_xticks([])
    tile.set_yticks([])
    for spine in tile.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(lw)
        spine.set_color(edge)
    return tile


def arrow(x1, y1, x2, y2, color=INK, dashed=False, curve=0.0, lw=0.9):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=lw,
            color=color,
            linestyle="--" if dashed else "-",
            connectionstyle=f"arc3,rad={curve}",
            shrinkA=0,
            shrinkB=0,
            zorder=20,
        )
    )


def scalar_rgb(values, cmap="viridis"):
    values = np.clip(values, 0.0, 1.0)
    return Image.fromarray((mpl.colormaps[cmap](values)[..., :3] * 255).astype(np.uint8))


def dimmed_crop(stem, object_id, padding=30):
    rgb = np.array(Image.open(RGB_ROOT / f"{stem}.jpg").convert("RGB"), dtype=np.float32)
    ids = np.array(Image.open(ASSET / "preprocessing" / "object_mask_refined" / f"{stem}.png"))
    mask = ids == object_id
    yy, xx = np.where(mask)
    x0, x1 = max(0, int(xx.min()) - padding), min(rgb.shape[1], int(xx.max()) + padding + 1)
    y0, y1 = max(0, int(yy.min()) - padding), min(rgb.shape[0], int(yy.max()) + padding + 1)
    crop = rgb[y0:y1, x0:x1]
    keep = mask[y0:y1, x0:x1]
    crop[~keep] = crop[~keep] * 0.18 + 255.0 * 0.82
    return Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8))


def crop_strip():
    objects = [dimmed_crop("08", 2), dimmed_crop("08", 5), dimmed_crop("08", 7)]
    width, height, gap = 310, 300, 8
    canvas = Image.new("RGB", (width * 3 + gap * 2, height), "white")
    for index, item in enumerate(objects):
        item.thumbnail((width, height), Image.Resampling.LANCZOS)
        x = index * (width + gap) + (width - item.width) // 2
        y = (height - item.height) // 2
        canvas.paste(item, (x, y))
    return canvas


def prediction_overlay(mask_path, color):
    rgb = np.array(Image.open(ASSET / "query" / "ipr" / "4" / "render_rgb.png").convert("RGB"), dtype=np.float32)
    pred_native = np.array(Image.open(mask_path).convert("L")) > 0
    gt_native = np.array(
        Image.open(ROOT / "dataset" / "3dovs" / "bench" / "test_mask" / "4" / "Portuguese egg tart.png").convert("L")
    ) > 0
    pred_eval = pred_native
    if pred_eval.shape != gt_native.shape:
        pred_eval = np.array(
            Image.fromarray((pred_eval * 255).astype(np.uint8)).resize(
                (gt_native.shape[1], gt_native.shape[0]), Image.Resampling.NEAREST
            )
        ) > 0
    intersection = np.logical_and(gt_native, pred_eval).sum()
    union = np.logical_or(gt_native, pred_eval).sum()
    iou = float(intersection / union) if union else 1.0

    pred = pred_native
    gt = gt_native
    if pred.shape != rgb.shape[:2]:
        pred = np.array(
            Image.fromarray((pred * 255).astype(np.uint8)).resize(
                (rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST
            )
        ) > 0
    if gt.shape != rgb.shape[:2]:
        gt = np.array(
            Image.fromarray((gt * 255).astype(np.uint8)).resize(
                (rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST
            )
        ) > 0
    tint = np.asarray(color, dtype=np.float32)
    rgb[pred] = rgb[pred] * 0.43 + tint * 0.57
    eroded = gt.copy()
    eroded[1:-1, 1:-1] &= gt[:-2, 1:-1] & gt[2:, 1:-1] & gt[1:-1, :-2] & gt[1:-1, 2:]
    rgb[gt & ~eroded] = 255.0
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), iou


stem = "08"
rgb = np.array(Image.open(RGB_ROOT / f"{stem}.jpg").convert("RGB"), dtype=np.float32)
ids = np.array(Image.open(ASSET / "preprocessing" / "object_mask_refined" / f"{stem}.png"))
semantics = json.loads(
    (ASSET / "preprocessing" / "object_mask_ipr_report" / "object_semantics.json").read_text(encoding="utf-8")
)

semantic_values = np.zeros(ids.shape, dtype=np.float32)
area_risk = np.zeros(ids.shape, dtype=bool)
for object_id, record in semantics["objects"].items():
    object_id_int = int(object_id)
    semantic_values[ids == object_id_int] = float(record.get("semantic_confidence", 0.0))
    area_risk[ids == object_id_int] = semantics["object_weights"][object_id]["reason"] == "large_mixed_region"

semantic_map = scalar_rgb(semantic_values)
risk_map = np.empty((*ids.shape, 3), dtype=np.uint8)
risk_map[area_risk] = np.array([193, 56, 59], dtype=np.uint8)
risk_map[~area_risk] = np.array([75, 151, 111], dtype=np.uint8)
risk_map = Image.fromarray(risk_map)

risk_overlay = rgb.copy()
risk_overlay[~area_risk] *= 0.22
risk_overlay[area_risk] = risk_overlay[area_risk] * 0.42 + np.array([200, 52, 58]) * 0.58
risk_overlay = Image.fromarray(np.clip(risk_overlay, 0, 255).astype(np.uint8))

official_result, official_iou = prediction_overlay(
    ASSET / "query" / "official" / "4" / "final_mask.png", (196, 76, 71)
)
ipr_result, ipr_iou = prediction_overlay(ASSET / "query" / "ipr" / "4" / "final_mask.png", (15, 165, 225))
crops = crop_strip()

# Top: the unchanged ILGS field and query representation.
text(27, 4.8, "Identity-aware language\n3D Gaussian field", 8.8, True, "center")
image_tile(ASSET / "query" / "ipr" / "4" / "render_rgb.png", 8, 13, 38, 27)
text(27, 42.4, "Novel view", 6.2, False, "center", "#555555")

ax.add_patch(
    FancyBboxPatch(
        (53, 2.5), 124, 38, boxstyle="round,pad=0,rounding_size=1.2",
        facecolor="#FAFAFA", edgecolor=INK, linewidth=0.8, zorder=1
    )
)
top_maps = [
    (ASSET / "query" / "ipr" / "4" / "language_latent_rgb.png", "Language feature"),
    (ASSET / "query" / "ipr" / "4" / "identity_labels.png", "Identity feature"),
    (ASSET / "query" / "ipr" / "4" / "segment_heatmap.png", "Segment similarity"),
]
for index, (path, title) in enumerate(top_maps):
    x = 57 + index * 39.0
    text(x + 16, 7.5, title, 5.9, False, "center")
    image_tile(path, x, 11, 32, 22)
text(115, 37, 'Text query  ->  "Portuguese egg tart"', 6.7, True, "center")
arrow(46.5, 25, 51.5, 22, "#44823E", dashed=True, curve=-0.1, lw=1.0)

# Bottom: make the problem, mechanism and benefit explicit.
ax.add_patch(
    FancyBboxPatch(
        (3.5, 47), 176, 70, boxstyle="round,pad=0,rounding_size=1.8",
        facecolor=PANEL, edgecolor="#33485F", linewidth=0.9, zorder=0
    )
)
text(7, 51, "IPR contribution: suppress noisy identity supervision without changing IDs", 7.8, True, color=BLUE)

centers = [20, 52, 84, 116, 154]
tile_w, tile_h = 27, 18
top_y, bottom_y = 58, 82.5

# Column 1: reveal the source problem with real labels and a red callout over the large regions.
source_ax = image_tile(
    ASSET / "preprocessing_visuals" / "object_mask" / f"{stem}.png",
    centers[0] - tile_w / 2, top_y, tile_w, tile_h, edge=RED, lw=0.9
)
source_ax.add_patch(Ellipse((0.72, 0.20), 0.50, 0.30, transform=source_ax.transAxes, fill=False,
                            edgecolor=YELLOW, linewidth=1.2, linestyle="--"))
source_ax.add_patch(Ellipse((0.62, 0.78), 0.70, 0.35, transform=source_ax.transAxes, fill=False,
                            edgecolor=YELLOW, linewidth=1.2, linestyle="--"))
image_tile(risk_overlay, centers[0] - tile_w / 2, bottom_y, tile_w, tile_h, edge=RED, lw=0.9)
text(centers[0], 55.2, "Mixed identity IDs", 5.8, True, "center", RED)
text(centers[0], 103.3, "wall / floor leakage", 5.5, False, "center", RED)

# Column 2: real crops provide semantic evidence while IDs remain unchanged.
image_tile(crops, centers[1] - tile_w / 2, top_y, tile_w, tile_h)
image_tile(semantic_map, centers[1] - tile_w / 2, bottom_y, tile_w, tile_h)
text(centers[1], 55.2, "Crop semantics", 5.8, True, "center")
text(centers[1], 103.3, "trusted objects", 5.5, False, "center", GREEN)

# Column 3: a dedicated map exposes the large-area failure mode.
image_tile(risk_overlay, centers[2] - tile_w / 2, top_y, tile_w, tile_h)
image_tile(risk_map, centers[2] - tile_w / 2, bottom_y, tile_w, tile_h)
text(centers[2], 55.2, "Area consistency", 5.8, True, "center")
text(centers[2], 103.3, r"mixed ID: $h_i=0.35$", 5.5, True, "center", RED)

# Column 4: show the actual confidence change, not a symbolic box.
image_tile(
    ASSET / "preprocessing_visuals" / "object_confidence_refined" / f"{stem}.png",
    centers[3] - tile_w / 2, top_y, tile_w, tile_h
)
image_tile(
    ASSET / "preprocessing_visuals" / "object_confidence_ipr" / f"{stem}.png",
    centers[3] - tile_w / 2, bottom_y, tile_w, tile_h, edge=GREEN, lw=0.9
)
text(centers[3], 55.2, "Base confidence", 5.8, True, "center")
text(centers[3], 103.3, "IPR reweighting", 5.5, True, "center", GREEN)

# Column 5: same query and decoder expose the actual advantage.
official_ax = image_tile(official_result, centers[4] - tile_w / 2, top_y, tile_w, tile_h, edge=RED, lw=1.0)
ipr_ax = image_tile(ipr_result, centers[4] - tile_w / 2, bottom_y, tile_w, tile_h, edge=GREEN, lw=1.0)
official_ax.add_patch(
    Ellipse(
        (0.315, 0.545), 0.20, 0.18,
        transform=official_ax.transAxes,
        fill=False,
        edgecolor=YELLOW,
        linewidth=1.1,
        linestyle="--",
    )
)
text(centers[4], 55.2, f"ILGS: wrong ID  IoU {official_iou:.3f}", 5.4, True, "center", RED)
text(centers[4], 79.4, "yellow circle: GT target", 4.8, True, "center", "#796A00")
text(centers[4], 103.3, f"+ IPR: target ID  IoU {ipr_iou:.3f}", 5.4, True, "center", GREEN)

for left, right in zip(centers[:-1], centers[1:]):
    arrow(left + 14.0, 67, right - 14.0, 67, RED if left < 84 else GREEN, lw=0.85)
    arrow(left + 14.0, 91.5, right - 14.0, 91.5, GREEN, lw=0.85)

# Vertical arrows distinguish the original path from the proposed reliability path.
for center in centers[:4]:
    arrow(center, 76.5, center, 81.7, YELLOW, lw=0.9)

ax.add_patch(Rectangle((18, 108.2), 129, 3.2, facecolor="#B9DCA9", edgecolor="#44823E", linewidth=0.6))
arrow(147, 109.8, 166, 109.8, "#44823E", lw=1.0)
text(84, 109.8, "detect mixed IDs  ->  estimate reliability  ->  down-weight noisy gradients", 6.8, True, "center")
text(176, 113.8, "+5.06 mIoU / +5.53 mBIoU", 5.6, True, "right", GREEN)

arrow(116, 47, 44, 42.2, GREEN, dashed=True, curve=-0.08, lw=1.0)
text(88, 45.0, "weighted identity supervision", 5.5, False, "center", GREEN)

base = OUT / "IPR_method_contribution"
fig.savefig(base.with_suffix(".svg"), dpi=300)
fig.savefig(base.with_suffix(".pdf"), dpi=300)
fig.savefig(base.with_suffix(".png"), dpi=600)
fig.savefig(OUT / "IPR_method_contribution_preview.png", dpi=200)

(OUT / "asset_provenance.json").write_text(
    json.dumps(
        {
            "scene": "3D-OVS Bench",
            "frame": stem,
            "query": "Portuguese egg tart",
            "query_view": 4,
            "official_iou": official_iou,
            "ipr_iou": ipr_iou,
            "ten_scene_multiseed_gain_miou": 5.06,
            "ten_scene_multiseed_gain_mbiou": 5.53,
            "asset_bundle": str(ASSET),
            "ai_generated_images": False,
            "fabricated_states": False,
        },
        indent=2,
    ),
    encoding="utf-8",
)
(OUT / "README.md").write_text(
    """# Contribution-oriented IPR method figure

This version makes the contribution explicit through an image-led before/after structure. The
upper row of the lower panel shows the original failure path: mixed wall/floor identity labels,
uniform base confidence and an incorrect ILGS query result. The lower row shows IPR: crop-based
semantic evidence, large-region risk detection, confidence reweighting without changing identity
IDs, and the corrected result under the same query and decoder.

All raster panels are real Bench artifacts or deterministic overlays. White output contours are
ground truth used only for visualization and IoU calculation. The reported ten-scene gains are
from the three-seed controlled 3D-OVS summary supplied by the experiment pipeline.
""",
    encoding="utf-8",
)
print(OUT)
