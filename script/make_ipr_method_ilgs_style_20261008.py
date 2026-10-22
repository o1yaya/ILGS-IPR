# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# Method schematic has no matching template; this layout follows the official ILGS visual grammar.
# Every raster tile is a real exported artifact or a deterministic visualization of one.
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ASSET = Path(r"D:\downloads\ipr_method_assets\bench_20261007_203512_313407")
RGB_ROOT = ROOT / "dataset" / "3dovs" / "bench" / "images"
OUT = ROOT / "outputs" / "method_figure_ilgs_style_20261008"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 183.0, 119.0
fig = plt.figure(figsize=(W / 25.4, H / 25.4), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set(xlim=(0, W), ylim=(H, 0))
ax.axis("off")

INK = "#222222"
GREEN = "#44823E"
GREEN_DARK = "#177560"
BLUE_PANEL = "#E6EBF5"
BLUE_EDGE = "#33485F"
YELLOW = "#E9D52D"
RED = "#C2383B"


def label(x, y, value, size=7, bold=False, ha="left", color=INK):
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


def image_tile(image_or_path, x, y, w, h, edge="#FFFFFF", lw=0.6):
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


def scalar_rgb(values, cmap="viridis", vmin=0.0, vmax=1.0):
    normalized = np.clip((values - vmin) / max(vmax - vmin, 1e-8), 0.0, 1.0)
    return Image.fromarray((mpl.colormaps[cmap](normalized)[..., :3] * 255).astype(np.uint8))


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
    items = [dimmed_crop("08", 2), dimmed_crop("08", 5), dimmed_crop("08", 7)]
    thumb_w, thumb_h, gap = 310, 300, 8
    canvas = Image.new("RGB", (thumb_w * 3 + gap * 2, thumb_h), "white")
    for index, item in enumerate(items):
        item = item.copy()
        item.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = index * (thumb_w + gap) + (thumb_w - item.width) // 2
        y = (thumb_h - item.height) // 2
        canvas.paste(item, (x, y))
    return canvas


stem = "08"
rgb = np.array(Image.open(RGB_ROOT / f"{stem}.jpg").convert("RGB"), dtype=np.float32)
ids = np.array(Image.open(ASSET / "preprocessing" / "object_mask_refined" / f"{stem}.png"))
id_visual = np.array(Image.open(ASSET / "preprocessing_visuals" / "object_mask_refined" / f"{stem}.png").convert("RGB"), dtype=np.float32)

semantics = json.loads(
    (ASSET / "preprocessing" / "object_mask_ipr_report" / "object_semantics.json").read_text(encoding="utf-8")
)
semantic_values = np.zeros(ids.shape, dtype=np.float32)
area_risk = np.zeros(ids.shape, dtype=np.float32)
reliability = np.zeros(ids.shape, dtype=np.float32)
for object_id, record in semantics["objects"].items():
    key = int(object_id)
    semantic_values[ids == key] = float(record.get("semantic_confidence", 0.0))
    weight_record = semantics["object_weights"][object_id]
    reliability[ids == key] = float(weight_record["semantic_weight"])
    area_risk[ids == key] = 1.0 if weight_record["reason"] == "large_mixed_region" else 0.0

semantic_map = scalar_rgb(semantic_values)
area_map = np.full((*ids.shape, 3), 238, dtype=np.uint8)
area_map[area_risk > 0] = np.array([190, 56, 59], dtype=np.uint8)
area_map[area_risk == 0] = np.array([77, 151, 112], dtype=np.uint8)
area_map = Image.fromarray(area_map)

identity_overlay = np.clip(rgb * 0.46 + id_visual * 0.54, 0, 255).astype(np.uint8)
identity_overlay = Image.fromarray(identity_overlay)

risk_overlay = rgb.copy()
risk_mask = area_risk > 0
risk_overlay[~risk_mask] *= 0.22
risk_overlay[risk_mask] = risk_overlay[risk_mask] * 0.44 + np.array([200, 55, 60]) * 0.56
risk_overlay = Image.fromarray(np.clip(risk_overlay, 0, 255).astype(np.uint8))

reliability_map = scalar_rgb(reliability)
crops = crop_strip()

# Top block: retain the official ILGS visual grammar for the trained field and query maps.
label(28, 4.5, "IPR-enhanced identity-aware\nlanguage 3D Gaussian field", 8.8, True, "center")
image_tile(ASSET / "query" / "ipr" / "4" / "render_rgb.png", 10, 13, 38, 27.5)
label(29, 43, "Novel view", 6.4, False, "center", "#555555")

ax.add_patch(
    FancyBboxPatch(
        (68, 2.5),
        108,
        38,
        boxstyle="round,pad=0,rounding_size=1.1",
        facecolor="#FAFAFA",
        edgecolor=INK,
        linewidth=0.8,
        zorder=1,
    )
)
top_tiles = [
    (ASSET / "query" / "ipr" / "4" / "language_latent_rgb.png", "Language feature\nmap"),
    (ASSET / "query" / "ipr" / "4" / "identity_labels.png", "Identity feature\nmap"),
    (ASSET / "query" / "ipr" / "4" / "segment_heatmap.png", "Segment-wise\ncosine similarity"),
]
for index, (path, title) in enumerate(top_tiles):
    x = 71 + index * 34.1
    label(x + 14.5, 8, title, 6.1, False, "center")
    image_tile(path, x, 13, 29, 20.5)
label(122, 37, 'Text query  ->  "Portuguese egg tart"', 6.8, True, "center")
arrow(48.5, 25, 66.5, 20.5, GREEN, dashed=True, curve=-0.15, lw=1.0)
label(57, 21, "Rasterize", 5.8, False, "center", "#555555")

# Bottom block: almost entirely real images, paired like the official ILGS mask-expansion panel.
ax.add_patch(
    FancyBboxPatch(
        (4, 49),
        175,
        66,
        boxstyle="round,pad=0,rounding_size=1.8",
        facecolor=BLUE_PANEL,
        edgecolor=BLUE_EDGE,
        linewidth=0.9,
        zorder=0,
    )
)

centers = [21, 55, 89, 123, 157]
tile_w, tile_h = 27.5, 19.5
top_y, bottom_y = 55, 80.5

top_items = [
    (RGB_ROOT / f"{stem}.jpg", "RGB views"),
    (ASSET / "preprocessing_visuals" / "object_mask" / f"{stem}.png", "Source IDs"),
    (crops, "Object crops"),
    (risk_overlay, "Mixed region"),
    (ASSET / "preprocessing_visuals" / "object_confidence_refined" / f"{stem}.png", "Base confidence"),
]
bottom_items = [
    (identity_overlay, "Identity mask"),
    (ASSET / "preprocessing_visuals" / "object_mask_refined" / f"{stem}.png", "Clean IDs"),
    (semantic_map, "Semantic support"),
    (area_map, "Area risk"),
    (ASSET / "preprocessing_visuals" / "object_confidence_ipr" / f"{stem}.png", "IPR confidence"),
]

for index, center in enumerate(centers):
    x = center - tile_w / 2
    top_path, top_title = top_items[index]
    bottom_path, bottom_title = bottom_items[index]
    image_tile(top_path, x, top_y, tile_w, tile_h)
    image_tile(bottom_path, x, bottom_y, tile_w, tile_h)
    label(center, 52.2, top_title, 5.8, False, "center")
    label(center, 102.4, bottom_title, 5.8, False, "center")
    ax.plot([center, center], [74.8, 80.2], color=YELLOW, linewidth=1.0, zorder=15)
    arrow(center, 78.0, center, 80.0, YELLOW, lw=0.9)

for left, right in zip(centers[:-1], centers[1:]):
    arrow(left + 14.4, 65.0, right - 14.4, 65.0, RED, lw=0.8)

ax.add_patch(Rectangle((20, 107.1), 137, 3.0, facecolor="#B9DCA9", edgecolor=GREEN, linewidth=0.6, zorder=5))
arrow(157, 108.6, 165, 108.6, GREEN, lw=1.0)
label(91, 108.7, "Identity-preserving pseudo-label reliability", 7.8, True, "center")

arrow(157, 49, 45, 42.2, GREEN_DARK, dashed=True, curve=-0.07, lw=1.0)
label(106, 46.5, "confidence-weighted identity supervision", 5.8, False, "center", GREEN_DARK)

base = OUT / "IPR_method_ILGS_style"
fig.savefig(base.with_suffix(".svg"), dpi=300)
fig.savefig(base.with_suffix(".pdf"), dpi=300)
fig.savefig(base.with_suffix(".png"), dpi=600)
fig.savefig(OUT / "IPR_method_ILGS_style_preview.png", dpi=200)

(OUT / "asset_provenance.json").write_text(
    json.dumps(
        {
            "layout_reference": "official ILGS method figure supplied by the user",
            "scene": "3D-OVS Bench",
            "frame": stem,
            "query_view": 4,
            "asset_bundle": str(ASSET),
            "derived_visuals": [
                "identity overlay",
                "three-object crop strip",
                "semantic-confidence map",
                "large-region risk map and overlay",
            ],
            "ai_generated_images": False,
            "fabricated_states": False,
        },
        indent=2,
    ),
    encoding="utf-8",
)
(OUT / "README.md").write_text(
    """# ILGS-style IPR method figure

This version deliberately follows the official ILGS visual grammar: the trained field and three
rasterized maps occupy the upper block, while a large two-row image panel explains the proposed
IPR supervision path. Text is restricted to short image labels and one pipeline title.

All panels are real Bench artifacts or deterministic visualizations of exported masks, confidence
values and object records. Source IDs and clean IDs are identical for frame 08 because no local
component was removed in that frame; the method still preserves the cleanup stage. No synthetic
mask-expansion state or AI-generated scientific image is used.
""",
    encoding="utf-8",
)
print(OUT)
