from __future__ import annotations

# Asset confirmation: scanned the Academic Figure Skill GroupedBarChart and
# PairedBoxScatter assets; reused their paired-comparison/error-bar conventions.
# The image panels reuse experiment outputs already present in this repository.

import argparse
from pathlib import Path
import matplotlib as mpl

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
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

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED = "#B2182B"
GREY = "#999999"
BLACK = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

MM_TO_INCH = 1 / 25.4
CONTROL, IPR = CATEGORICAL[0], CATEGORICAL[2]
BOUNDARY, NEGATIVE = CATEGORICAL[3], ACCENT_RED
LIGHT_GREY, MID_GREY = "#D9D9D9", "#6B7280"

SCENES = ["Bed", "Bench", "Blue Sofa", "Covered Desk", "Lawn",
          "Office Desk", "Room", "Snacks", "Sofa", "Table"]
OFFICIAL_MIOU = np.array([92.11, 81.36, 72.11, 78.90, 97.09, 90.15, 77.26, 77.47, 71.69, 81.98])
OFFICIAL_MIOU_SD = np.array([9.36, 0.30, 8.15, 1.59, 0.04, 10.35, 9.42, 7.75, 1.74, 0.09])
IPR_MIOU = np.array([92.21, 95.84, 89.56, 76.75, 97.16, 96.04, 82.83, 85.57, 72.57, 82.23])
IPR_MIOU_SD = np.array([9.39, 0.02, 10.44, 3.49, 0.04, 0.02, 9.66, 0.05, 0.44, 0.03])
OFFICIAL_BIOU = np.array([86.34, 76.27, 66.97, 69.76, 92.78, 83.82, 72.03, 71.59, 64.94, 72.44])
OFFICIAL_BIOU_SD = np.array([10.65, 0.33, 9.02, 1.18, 0.29, 11.80, 9.95, 8.12, 1.98, 0.09])
IPR_BIOU = np.array([87.13, 91.01, 85.17, 67.77, 93.02, 90.35, 77.51, 80.81, 65.84, 73.62])
IPR_BIOU_SD = np.array([10.28, 0.08, 11.01, 1.86, 0.21, 0.06, 10.22, 0.19, 0.67, 0.14])

def panel_label(ax, label, x=-0.12, y=1.04):
    ax.text(x, y, label, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="top")

def make_ablation_diagnostic(repo, outdir):
    delta_miou = np.array([3.74, 3.51, 2.54, 1.98, 1.82, 1.45, -0.15, -1.63])
    delta_biou = np.array([3.21, 2.85, 2.53, 2.17, 1.89, 0.89, 0.39, -1.07])
    display = ["No visibility (selected IPR)", "No semantic", "Large only", "No large",
               "Cleanup + confidence", "Full", "Semantic only", "Cleanup"]
    source = repo / "outputs/ipr_noise_examples_local_test/bench_20261007_203512_313407/best"
    image_paths = [source / name for name in
                   ("rgb.png", "identity_ids_labeled.png",
                    "large_region_highlight.png", "ipr_confidence.png")]
    missing = [str(p) for p in image_paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing diagnostic assets: " + ", ".join(missing))

    fig = plt.figure(figsize=(183 * MM_TO_INCH, 108 * MM_TO_INCH), facecolor="white")
    gs = fig.add_gridspec(2, 3, width_ratios=[1.18, 1, 1],
                          left=0.07, right=0.985, top=0.94, bottom=0.17,
                          wspace=0.20, hspace=0.24)
    ax = fig.add_subplot(gs[:, 0])
    image_axes = [fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2]),
                  fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[1, 2])]
    y = np.arange(len(display))
    ax.axvline(0, color="#777777", linewidth=0.7, linestyle="--", zorder=0)
    ax.axhspan(-0.42, 0.42, color="#E8F3EA", zorder=-2)
    for yi, dm, db in zip(y, delta_miou, delta_biou):
        ax.plot([min(dm, db, 0), max(dm, db, 0)], [yi, yi],
                color=LIGHT_GREY, linewidth=1.2, zorder=1)
    # Asset source: paired-comparison convention adapted from PairedBoxScatter.
    ax.scatter(delta_miou, y, s=28, marker="o", facecolor=CONTROL,
               edgecolor="white", linewidth=0.5, zorder=3)
    ax.scatter(delta_biou, y, s=27, marker="s", facecolor=BOUNDARY,
               edgecolor="white", linewidth=0.5, zorder=3)
    for yi, dm, db in zip(y, delta_miou, delta_biou):
        for value, offset in ((dm, 0.10), (db, -0.10)):
            ax.text(value + (0.10 if value >= 0 else -0.10), yi + offset,
                    f"{value:+.2f}", fontsize=5.6,
                    color=NEGATIVE if value < 0 else MID_GREY, va="center",
                    ha="left" if value >= 0 else "right")
    ax.set_yticks(y, display)
    ax.invert_yaxis()
    ax.set_xlim(-2.4, 4.7)
    ax.set_xticks([-2, 0, 2, 4])
    ax.set_xlabel("Gain over official ILGS (percentage points)")
    ax.set_title("LERF component evidence", loc="left", fontweight="bold", pad=8)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#E6E6E6", linewidth=0.45, zorder=-3)
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CONTROL,
               markeredgecolor="white", markersize=5.5, label="mIoU"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=BOUNDARY,
               markeredgecolor="white", markersize=5.2, label="mBIoU")],
        loc="lower right", ncol=2, handletextpad=0.3, columnspacing=0.8)
    panel_label(ax, "a", x=-0.22)

    titles = ["RGB input", "Noisy identity IDs",
              "Large-region flags", "IPR reliability map"]
    for img_ax, img_path, title, label in zip(image_axes, image_paths, titles, "bcde"):
        img_ax.imshow(plt.imread(img_path))
        img_ax.set_title(title, fontweight="bold", pad=4)
        img_ax.set_xticks([])
        img_ax.set_yticks([])
        for spine in img_ax.spines.values():
            spine.set_visible(False)
        panel_label(img_ax, label, x=-0.07, y=1.08)
    fig.text(0.745, 0.045,
             "Bench frame 12: wall ID 6 = 42.3%; floor ID 4 = 43.3%",
             ha="center", va="center", fontsize=6.5, color=MID_GREY)
    fig.text(0.21, 0.045,
             "Scene-equal means; three training seeds per scene. No inferential test.",
             ha="center", va="center", fontsize=6.2, color=MID_GREY)
    stem = outdir / "fig3_ablation_reliability_diagnostic"
    save_cns_figure(fig, stem)
    fig.savefig(f"{stem}.svg", bbox_inches="tight", dpi=300)
    plt.close(fig)

def draw_seed_comparison(ax, control, control_sd, ipr, ipr_sd,
                         title, overall_gain, xlim, show_y):
    gains = ipr - control
    order = np.argsort(IPR_MIOU - OFFICIAL_MIOU)[::-1]
    y = np.arange(len(order))
    for yi, idx in zip(y, order):
        ax.plot([control[idx], ipr[idx]], [yi, yi],
                color=LIGHT_GREY, linewidth=1.25, zorder=1)
    # Asset source: error-bar and connector conventions adapted from skill assets.
    ax.errorbar(control[order], y, xerr=control_sd[order], fmt="o",
                color=CONTROL, markerfacecolor=CONTROL, markeredgecolor="white",
                markeredgewidth=0.55, markersize=4.7,
                elinewidth=0.8, capsize=1.8, zorder=3)
    ax.errorbar(ipr[order], y, xerr=ipr_sd[order], fmt="s",
                color=IPR, markerfacecolor=IPR, markeredgecolor="white",
                markeredgewidth=0.55, markersize=4.5,
                elinewidth=0.8, capsize=1.8, zorder=4)
    for yi, idx in zip(y, order):
        gain = gains[idx]
        ax.text(xlim[1] - 0.7, yi, f"{gain:+.2f}", ha="right", va="center",
                fontsize=6.1, color=IPR if gain >= 0 else NEGATIVE,
                fontweight="bold" if abs(gain) >= 5 else "normal")
    ax.set_ylim(len(order) - 0.35, -1.15)
    ax.set_xlim(*xlim)
    ax.set_xlabel("Score (%)")
    ax.set_title(title, loc="left", fontweight="bold", pad=7)
    ax.set_yticks(y)
    if show_y:
        ax.set_yticklabels([SCENES[i] for i in order])
        ax.tick_params(axis="y", length=0)
    else:
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#E6E6E6", linewidth=0.45, zorder=-3)
    ax.text(0.99, 1.02, f"10-scene mean gain: {overall_gain:+.2f}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.7,
            color=IPR, fontweight="bold")

def make_ten_scene_robustness(outdir):
    fig, axes = plt.subplots(
        1, 2, figsize=(183 * MM_TO_INCH, 101 * MM_TO_INCH), sharey=True,
        gridspec_kw={"left": 0.11, "right": 0.985, "top": 0.88,
                     "bottom": 0.18, "wspace": 0.10})
    draw_seed_comparison(axes[0], OFFICIAL_MIOU, OFFICIAL_MIOU_SD,
                         IPR_MIOU, IPR_MIOU_SD,
                         "mIoU across 3D-OVS scenes", 5.06, (56, 104), True)
    draw_seed_comparison(axes[1], OFFICIAL_BIOU, OFFICIAL_BIOU_SD,
                         IPR_BIOU, IPR_BIOU_SD,
                         "mBIoU across 3D-OVS scenes", 5.53, (51, 104), False)
    panel_label(axes[0], "a", x=-0.20)
    panel_label(axes[1], "b", x=-0.08)
    handles = [
        Line2D([0], [0], marker="o", color=CONTROL, markerfacecolor=CONTROL,
               markeredgecolor="white", markersize=5.5, linewidth=0.8,
               label="Official ILGS"),
        Line2D([0], [0], marker="s", color=IPR, markerfacecolor=IPR,
               markeredgecolor="white", markersize=5.2, linewidth=0.8,
               label="ILGS + IPR")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.985),
               ncol=2, handletextpad=0.5, columnspacing=1.5)
    fig.text(0.5, 0.06,
             "Points show mean ± sample SD from three independent training seeds. "
             "Right labels show IPR - official ILGS.",
             ha="center", va="center", fontsize=6.6, color=MID_GREY)
    stem = outdir / "fig4_ten_scene_multiseed_robustness"
    save_cns_figure(fig, stem)
    fig.savefig(f"{stem}.svg", bbox_inches="tight", dpi=300)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    make_ablation_diagnostic(args.repo, args.outdir)
    make_ten_scene_robustness(args.outdir)
    print(args.outdir)

if __name__ == "__main__":
    main()
