from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.patches import Rectangle


ROOT = Path("server_snapshot/ilgs_controlled_ablation/output/lerf")
OUTPUT = Path(r"D:\wlxy\ilgs\文章图\ablation_visual_20261021")

EXAMPLES = [
    {
        "scene": "ramen",
        "frame": "3",
        "query": "pork belly",
        "label": '(a) Ramen  |  query: "pork belly"',
        "roi": (280, 205, 800, 575),
    },
    {
        "scene": "figurines",
        "frame": "3",
        "query": "old camera",
        "label": '(b) Figurines  |  query: "old camera"',
        "roi": (500, 185, 965, 535),
    },
]

METHODS = [
    ("RGB", None),
    ("Controlled ILGS", "official"),
    ("Cleanup + confidence", "cleanup_conf"),
    ("Full IPR", "full"),
]

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.linewidth": 0.6,
    }
)


def model_dir(scene: str, variant: str) -> Path:
    return ROOT / f"{scene}_ipr_{variant}_s0" / "test" / "ours_30000_text"


def load_rgb(scene: str, frame: str) -> np.ndarray:
    path = model_dir(scene, "official") / "renders" / f"{int(frame):05d}.png"
    return np.asarray(Image.open(path).convert("RGB"))


def load_mask(scene: str, variant: str, frame: str, query: str) -> np.ndarray:
    path = model_dir(scene, variant) / "test_mask" / frame / f"{query}.png"
    mask = np.asarray(Image.open(path).convert("L")) > 127
    return mask


def edge(mask: np.ndarray) -> np.ndarray:
    eroded = mask.copy()
    eroded[1:, :] &= mask[:-1, :]
    eroded[:-1, :] &= mask[1:, :]
    eroded[:, 1:] &= mask[:, :-1]
    eroded[:, :-1] &= mask[:, 1:]
    return mask & ~eroded


def overlay_prediction(rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    source = rgb.astype(np.float32) / 255.0
    gray = np.dot(source[..., :3], np.array([0.299, 0.587, 0.114]))
    output = np.repeat((0.52 * gray)[..., None], 3, axis=2)
    fill = np.array([1.00, 0.18, 0.10], dtype=np.float32)
    outline = np.array([1.00, 0.92, 0.05], dtype=np.float32)
    output[mask] = 0.18 * source[mask] + 0.82 * fill
    output[edge(mask)] = outline
    return np.clip(output, 0, 1)


def target_roi(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        return (0, 0, mask.shape[1], mask.shape[0])
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    pad = int(0.08 * max(x1 - x0, y1 - y0)) + 8
    x0, x1 = max(0, x0 - pad), min(mask.shape[1], x1 + pad)
    y0, y1 = max(0, y0 - pad), min(mask.shape[0], y1 + pad)
    return x0, y0, x1, y1


def add_query_box(
    ax,
    mask: np.ndarray,
    roi: tuple[int, int, int, int] | None = None,
) -> None:
    if not np.any(mask):
        return
    if roi is None:
        x0, y0, x1, y1 = target_roi(mask)
        pad_x = 0.02 * mask.shape[1]
        pad_y = 0.02 * mask.shape[0]
        x0 = max(0, x0 - pad_x)
        y0 = max(0, y0 - pad_y)
        x1 = min(mask.shape[1], x1 + pad_x)
        y1 = min(mask.shape[0], y1 + pad_y)
    else:
        x0, y0, x1, y1 = roi
    ax.add_patch(
        Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            fill=False,
            edgecolor="#FFD400",
            linewidth=1.35,
        )
    )
    ax.text(
        x0,
        max(0, y0 - 5),
        "QUERY TARGET",
        ha="left",
        va="bottom",
        fontsize=5.2,
        fontweight="bold",
        color="#202124",
        bbox={
            "boxstyle": "square,pad=0.14",
            "facecolor": "#FFD400",
            "edgecolor": "none",
        },
    )


def style_panel(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_panel(ax, panel: np.ndarray) -> None:
    ax.imshow(panel)
    style_panel(ax)


def save_figure() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7.20, 3.55), constrained_layout=False)
    grid = fig.add_gridspec(
        nrows=2,
        ncols=4,
        left=0.020,
        right=0.998,
        top=0.915,
        bottom=0.080,
        wspace=0.045,
        hspace=0.08,
    )

    for row, example in enumerate(EXAMPLES):
        rgb = load_rgb(example["scene"], example["frame"])
        full_mask = load_mask(
            example["scene"], "full", example["frame"], example["query"]
        )
        for col, (title, variant) in enumerate(METHODS):
            ax = fig.add_subplot(grid[row, col])
            if variant is None:
                panel = rgb.astype(np.float32) / 255.0
            else:
                mask = load_mask(
                    example["scene"], variant, example["frame"], example["query"]
                )
                panel = overlay_prediction(rgb, mask)
            draw_panel(ax, panel)
            if variant is None:
                add_query_box(ax, full_mask, example.get("roi"))
            if row == 0:
                ax.set_title(
                    title,
                    fontsize=7.3,
                    fontweight="bold" if variant == "full" else "normal",
                    color="#087F6B" if variant == "full" else "#202124",
                    pad=4,
                )
            if col == 0:
                ax.text(
                    0.0,
                    0.98,
                    example["label"],
                    transform=ax.transAxes,
                    ha="left",
                    va="top",
                    fontsize=6.5,
                    fontweight="bold",
                    color="white",
                    bbox={
                        "boxstyle": "square,pad=0.16",
                        "facecolor": "#202124",
                        "edgecolor": "none",
                        "alpha": 0.86,
                    },
                    clip_on=False,
                )

    fig.text(
        0.5,
        0.018,
        "Representative test views. Coral shows the predicted mask; yellow outlines mark its boundary. Each row uses one fixed view and query.",
        ha="center",
        va="bottom",
        fontsize=6.4,
        color="#5F6368",
    )

    stem = OUTPUT / "fig_ablation_visual"
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight", pad_inches=0.02)
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.02)
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(stem.with_suffix(".tiff"), dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


if __name__ == "__main__":
    save_figure()
