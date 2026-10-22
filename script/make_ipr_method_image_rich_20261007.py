# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a-c) method schematic -> other/ has no matching script -> custom vector layout
# All raster panels are exported model/data artifacts or deterministic composites.
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
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ASSET = Path(r"D:\downloads\ipr_method_assets\bench_20261007_203512_313407")
OUT = ROOT / "outputs" / "method_figure_image_rich_20261007"
OUT.mkdir(parents=True, exist_ok=True)
RGB_SOURCE = ROOT / "dataset" / "3dovs" / "bench" / "images"

W_MM, H_MM = 183.0, 140.0
FIG = plt.figure(figsize=(W_MM / 25.4, H_MM / 25.4), facecolor="white")
AX = FIG.add_axes([0, 0, 1, 1])
AX.set(xlim=(0, W_MM), ylim=(H_MM, 0))
AX.axis("off")

INK = "#243138"
GREEN = "#177560"
BLUE = "#2166AC"
RED = "#B2182B"
MUTED = "#647278"


def text(x, y, value, size=7, color=INK, bold=False, ha="left"):
    return AX.text(
        x,
        y,
        value,
        fontsize=size,
        color=color,
        weight="bold" if bold else "normal",
        ha=ha,
        va="center",
        linespacing=1.15,
        zorder=20,
    )


def band(x, y, w, h, fill, edge):
    AX.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=1.4",
            facecolor=fill,
            edgecolor=edge,
            linewidth=0.75,
            zorder=0,
        )
    )


def arrow(x1, y1, x2, y2, color=INK, lw=0.9):
    AX.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=lw,
            color=color,
            shrinkA=0,
            shrinkB=0,
            zorder=15,
        )
    )


def image_panel(image_or_path, x, y, w, h, border="#FFFFFF", lw=0.7, crop=True):
    image = image_or_path if isinstance(image_or_path, Image.Image) else Image.open(image_or_path)
    axes = FIG.add_axes([x / W_MM, 1 - (y + h) / H_MM, w / W_MM, h / H_MM], zorder=5)
    axes.imshow(image)
    axes.set_aspect("auto" if crop else "equal")
    axes.set_xticks([])
    axes.set_yticks([])
    for spine in axes.spines.values():
        spine.set_visible(True)
        spine.set_color(border)
        spine.set_linewidth(lw)
    return axes


def dimmed_object_crop(stem, object_id, pad=24, dim=0.20):
    rgb = np.array(Image.open(RGB_SOURCE / f"{stem}.jpg").convert("RGB"))
    labels = np.array(Image.open(ASSET / "preprocessing" / "object_mask_refined" / f"{stem}.png"))
    mask = labels == object_id
    yy, xx = np.where(mask)
    x0 = max(0, int(xx.min()) - pad)
    x1 = min(rgb.shape[1], int(xx.max()) + pad + 1)
    y0 = max(0, int(yy.min()) - pad)
    y1 = min(rgb.shape[0], int(yy.max()) + pad + 1)
    crop = rgb[y0:y1, x0:x1].astype(np.float32)
    crop_mask = mask[y0:y1, x0:x1]
    crop[~crop_mask] = crop[~crop_mask] * dim + 255.0 * (1.0 - dim)
    return Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8))


def mask_overlay(rgb_path, mask_path, gt_path, color):
    rgb = np.array(Image.open(rgb_path).convert("RGB"), dtype=np.float32)
    pred_native = np.array(Image.open(mask_path).convert("L")) > 0
    gt_native = np.array(Image.open(gt_path).convert("L")) > 0
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
    tint = np.array(color, dtype=np.float32)
    rgb[pred] = rgb[pred] * 0.43 + tint * 0.57
    eroded = gt.copy()
    eroded[1:-1, 1:-1] &= gt[:-2, 1:-1] & gt[2:, 1:-1] & gt[1:-1, :-2] & gt[1:-1, 2:]
    boundary = gt & ~eroded
    rgb[boundary] = np.array([255, 255, 255], dtype=np.float32)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), iou


query_root = ASSET / "query"
query_view = "4"
gt_path = ROOT / "dataset" / "3dovs" / "bench" / "test_mask" / query_view / "Portuguese egg tart.png"
render_path = query_root / "ipr" / query_view / "render_rgb.png"
official_overlay, official_iou = mask_overlay(
    render_path,
    query_root / "official" / query_view / "final_mask.png",
    gt_path,
    (196, 76, 71),
)
ipr_overlay, ipr_iou = mask_overlay(
    render_path,
    query_root / "ipr" / query_view / "final_mask.png",
    gt_path,
    (24, 145, 109),
)

evidence = {
    "egg": dimmed_object_crop("08", 2),
    "grape": dimmed_object_crop("08", 5),
}
mixed_rgb = np.array(Image.open(RGB_SOURCE / "08.jpg").convert("RGB"), dtype=np.float32)
mixed_labels = np.array(Image.open(ASSET / "preprocessing" / "object_mask_refined" / "08.png"))
mixed = mixed_labels == 4
mixed_rgb[~mixed] *= 0.18
mixed_rgb[mixed] = mixed_rgb[mixed] * 0.55 + np.array([190, 58, 55]) * 0.45
evidence["mixed"] = Image.fromarray(np.clip(mixed_rgb, 0, 255).astype(np.uint8))


text(4, 5, "Identity-preserving pseudo-label reliability for ILGS", 10, bold=True)
text(179, 5, "image-led overview", 6.3, color=GREEN, ha="right")

# a. Offline IPR supervision preparation.
band(3, 10, 177, 43, "#EEF7F2", GREEN)
text(6, 14, "a  Offline IPR supervision", 8, color=GREEN, bold=True)

image_panel(RGB_SOURCE / "00.jpg", 6.3, 19.2, 20, 15, border="#D2DADB")
image_panel(RGB_SOURCE / "08.jpg", 8.6, 17.2, 20, 15, border="#FFFFFF")
text(17.5, 37.0, "Multi-view RGB", 5.9, ha="center")

image_panel(ASSET / "preprocessing_visuals" / "object_mask" / "08.png", 34, 17.2, 20, 15)
text(44, 37.0, "Source IDs", 5.9, ha="center")
arrow(29.5, 25, 32.5, 25, GREEN)

image_panel(ASSET / "preprocessing_visuals" / "object_mask_refined" / "08.png", 59, 17.2, 20, 15)
text(69, 37.0, "Clean IDs", 5.9, ha="center")
arrow(54.5, 25, 57.5, 25, GREEN)

image_panel(evidence["egg"], 84, 17.2, 9.6, 15, border=GREEN, lw=1.0)
image_panel(evidence["grape"], 94.5, 17.2, 9.6, 15, border=GREEN, lw=1.0)
image_panel(evidence["mixed"], 105, 17.2, 9.6, 15, border=RED, lw=1.0)
text(99.3, 37.0, "crop semantics + area", 5.8, ha="center")
text(88.8, 40.8, "1.0", 5.4, color=GREEN, bold=True, ha="center")
text(99.3, 40.8, "1.0", 5.4, color=GREEN, bold=True, ha="center")
text(109.8, 40.8, "0.35", 5.4, color=RED, bold=True, ha="center")
arrow(79.8, 25, 82.5, 25, GREEN)

image_panel(
    ASSET / "preprocessing_visuals" / "object_confidence_refined" / "08.png",
    120,
    17.2,
    23,
    17.2,
)
text(131.5, 38.3, r"Base $c_t^0$", 5.9, ha="center")
arrow(115.5, 25, 118.5, 25, GREEN)

image_panel(
    ASSET / "preprocessing_visuals" / "object_confidence_ipr" / "08.png",
    150,
    17.2,
    23,
    17.2,
)
text(161.5, 38.3, r"IPR $w_t$", 5.9, color=GREEN, bold=True, ha="center")
arrow(144.2, 25, 148.5, 25, GREEN)
text(146.0, 46.8, r"$w_t(x)=\mathrm{clip}\!\left(c_t^0(x)h_t(x),0.05,1\right)$", 7.0, color=GREEN, ha="center")

# b. The refined labels and confidence weights enter the existing ILGS training path.
band(3, 57, 177, 35, "#EEF3F8", BLUE)
text(6, 61, "b  Confidence-weighted ILGS training", 8, color=BLUE, bold=True)

image_panel(ASSET / "preprocessing_visuals" / "object_mask_refined" / "08.png", 7, 67, 21, 15.8)
text(17.5, 86.0, r"$\widetilde{Y}_t$", 6.7, ha="center")
image_panel(ASSET / "preprocessing_visuals" / "object_confidence_ipr" / "08.png", 33, 67, 21, 15.8)
text(43.5, 86.0, r"$w_t(x)$", 6.7, ha="center")
arrow(55, 74.9, 62, 74.9, GREEN)

text(70.5, 70.6, "weighted ID loss", 6.2, bold=True, ha="center")
text(70.5, 77.5, r"$\mathcal{L}_{ID}^{w}=\frac{\sum_x w_t\ell_t}{\sum_x w_t}$", 7.4, ha="center")
arrow(80, 74.9, 86, 74.9, BLUE)

field_paths = [
    (query_root / "ipr" / query_view / "render_rgb.png", "RGB"),
    (query_root / "ipr" / query_view / "language_latent_rgb.png", "Language"),
    (query_root / "ipr" / query_view / "identity_feature_pca.png", "Identity"),
    (query_root / "ipr" / query_view / "identity_labels.png", "Segments"),
]
for index, (path, label) in enumerate(field_paths):
    x = 88 + index * 22.1
    image_panel(path, x, 67, 20, 15)
    text(x + 10, 85.4, label, 5.5, ha="center")
text(132.5, 89.2, "identity-aware language 3D Gaussian field", 5.6, color=BLUE, bold=True, ha="center")

# c. Shared decoder and a real matched output comparison.
band(3, 96, 177, 39.5, "#F5F4F8", "#786596")
text(6, 100, "c  Shared text-query decoder", 8, color="#665285", bold=True)
text(177, 100, 'query: "Portuguese egg tart"', 6.0, color="#665285", bold=True, ha="right")

query_tiles = [
    (query_root / "ipr" / query_view / "language_latent_rgb.png", "Language"),
    (query_root / "ipr" / query_view / "identity_labels.png", "Identity"),
    (query_root / "ipr" / query_view / "cosine_heatmap.png", "Cosine"),
    (query_root / "ipr" / query_view / "segment_heatmap.png", "Segment"),
]
for index, (path, label) in enumerate(query_tiles):
    x = 6 + index * 28.4
    image_panel(path, x, 105, 25, 18.75)
    text(x + 12.5, 127.2, label, 5.7, ha="center")
    if index < 3:
        arrow(x + 25.7, 114.4, x + 27.3, 114.4, "#665285", lw=0.8)

image_panel(official_overlay, 119.6, 105, 25, 18.75, border=RED, lw=1.0)
text(132.1, 127.2, f"ILGS  IoU {official_iou:.3f}", 5.7, color=RED, bold=True, ha="center")
arrow(116.5, 114.4, 118.2, 114.4, "#665285", lw=0.8)

image_panel(ipr_overlay, 148, 105, 25, 18.75, border=GREEN, lw=1.0)
text(160.5, 127.2, f"ILGS + IPR  IoU {ipr_iou:.3f}", 5.7, color=GREEN, bold=True, ha="center")
arrow(145.0, 114.4, 146.7, 114.4, GREEN, lw=0.9)

text(4, 138.1, "Real Bench artifacts; white contour denotes ground truth in the two output panels.", 5.3, color=MUTED)

base = OUT / "IPR_method_image_rich"
FIG.savefig(base.with_suffix(".svg"), dpi=300)
FIG.savefig(base.with_suffix(".pdf"), dpi=300)
FIG.savefig(base.with_suffix(".png"), dpi=600)
FIG.savefig(OUT / "IPR_method_image_rich_preview.png", dpi=200)

provenance = {
    "scene": "3D-OVS Bench",
    "frame_for_preprocessing": "08",
    "query": "Portuguese egg tart",
    "query_view": 4,
    "official_iou": official_iou,
    "ipr_iou": ipr_iou,
    "asset_bundle": str(ASSET),
    "ground_truth": str(gt_path),
    "derived_visuals": [
        "masked object crops from frame 08",
        "red/green prediction overlays with a white ground-truth contour",
    ],
    "fabricated_intermediate_states": False,
    "ai_generated_images": False,
}
(OUT / "asset_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
(OUT / "README.md").write_text(
    """# Image-rich IPR method figure

The figure uses exported Bench artifacts throughout: RGB views, source/refined identity maps,
base/IPR confidence maps, rendered language and identity features, similarity maps, and query
predictions. Object crops and output overlays are deterministic visual composites of those files.

The selected Bench frame has no local-component label change, so source and cleaned IDs are
visually identical. The confidence change is nevertheless real: large mixed regions receive
weight 0.35 while trusted object identities receive weight 1.0. No intermediate expansion frame
was invented; the recorded seed-ref decoder contained one state for this view.

Output panels use the same query and view. White contours denote ground truth and are used only
for visual evaluation, never for pseudo-label construction or training.
""",
    encoding="utf-8",
)
print(OUT)
