#!/usr/bin/env python3
"""Generate publication-ready quantitative figures from final IPR CSV reports."""

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl
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

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,         # TrueType font embedding
    "svg.fonttype": "none",     # editable text in SVG
    "savefig.bbox": "tight",    # trim whitespace
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)


import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


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


MM = 1 / 25.4
BLUE = CATEGORICAL[0]
GREEN = CATEGORICAL[2]
ORANGE = CATEGORICAL[3]
LIGHT_GREY = "#D4D4D4"
MID_GREY = "#777777"


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("seed", "mIoU", "mBIoU", "threshold", "mean_mIoU", "mean_mBIoU"):
            if key in row and row[key] != "":
                row[key] = float(row[key])
    return rows


def group_values(rows, variant, metric):
    grouped = defaultdict(dict)
    for row in rows:
        if row["variant"] == variant:
            grouped[row["scene"]][int(row["seed"])] = float(row[metric])
    return grouped


def seed_macro(grouped, scenes):
    seeds = sorted(set.intersection(*(set(grouped[scene]) for scene in scenes)))
    return np.array([
        np.mean([grouped[scene][seed] for scene in scenes])
        for seed in seeds
    ])


def finish_axis(ax, ylabel=None, xlabel=None):
    if ylabel:
        ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    ax.tick_params(length=3, color="#555555")
    ax.spines["left"].set_color("#555555")
    ax.spines["bottom"].set_color("#555555")
    ax.grid(axis="y", color="#E6E6E6", linewidth=0.45, zorder=0)


def panel_label(ax, label):
    ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="top", ha="left")


def save_all(fig, output_base):
    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight", dpi=600)
    fig.savefig(output_base.with_suffix(".png"), bbox_inches="tight", dpi=600)
    plt.close(fig)


def plot_lerf_paired(rows, output_dir):
    scenes = ["ramen", "figurines", "teatime"]
    labels = ["Ramen", "Figurines", "Teatime", "Mean"]
    variants = ("official", "strict_trainview_consistency")
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 72 * MM))

    for ax, metric, title in zip(axes, ("mIoU", "mBIoU"), ("Region accuracy", "Boundary accuracy")):
        values = {variant: group_values(rows, variant, metric) for variant in variants}
        for scene_index, scene in enumerate(scenes):
            seeds = sorted(set(values[variants[0]][scene]) & set(values[variants[1]][scene]))
            for seed in seeds:
                y0 = values[variants[0]][scene][seed]
                y1 = values[variants[1]][scene][seed]
                ax.plot([scene_index - 0.12, scene_index + 0.12], [y0, y1],
                        color=LIGHT_GREY, linewidth=0.8, zorder=1)
            for offset, variant, color, marker in (
                (-0.12, variants[0], BLUE, "o"),
                (0.12, variants[1], GREEN, "D"),
            ):
                vals = np.array([values[variant][scene][seed] for seed in seeds])
                ax.scatter(np.full(len(vals), scene_index + offset), vals,
                           color=color, marker=marker, s=16, alpha=0.55,
                           edgecolors="white", linewidths=0.35, zorder=2)
                ax.errorbar(scene_index + offset, vals.mean(), yerr=vals.std(ddof=1),
                            color=color, marker=marker, markersize=4.8,
                            markeredgecolor="white", markeredgewidth=0.45,
                            capsize=2.5, linewidth=1.1, zorder=3)

        mean_index = len(scenes)
        for offset, variant, color, marker in (
            (-0.12, variants[0], BLUE, "o"),
            (0.12, variants[1], GREEN, "D"),
        ):
            vals = seed_macro(values[variant], scenes)
            ax.scatter(np.full(len(vals), mean_index + offset), vals,
                       color=color, marker=marker, s=16, alpha=0.55,
                       edgecolors="white", linewidths=0.35, zorder=2)
            ax.errorbar(mean_index + offset, vals.mean(), yerr=vals.std(ddof=1),
                        color=color, marker=marker, markersize=5.1,
                        markeredgecolor="white", markeredgewidth=0.45,
                        capsize=2.5, linewidth=1.1, zorder=3)
            ax.text(mean_index + offset, vals.mean() + 1.0, f"{vals.mean():.2f}",
                    color=color, ha="center", va="bottom", fontsize=6.2)

        ax.set_title(title, fontweight="bold", pad=5)
        ax.set_xticks(range(len(labels)), labels)
        ax.set_xlim(-0.55, len(labels) - 0.45)
        ax.set_ylim(48 if metric == "mIoU" else 45, 87 if metric == "mIoU" else 82)
        finish_axis(ax, ylabel=f"{metric} (%)")

    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    handles = [
        mpl.lines.Line2D([], [], color=BLUE, marker="o", linestyle="none", markersize=5,
                         label="Controlled ILGS"),
        mpl.lines.Line2D([], [], color=GREEN, marker="D", linestyle="none", markersize=5,
                         label="Controlled ILGS + IPR"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.03))
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.18, top=0.79, wspace=0.26)
    save_all(fig, output_dir / "fig_exp_lerf_paired")


def plot_3dovs_gains(rows, output_dir):
    baseline = group_values(rows, "official", "mIoU")
    ipr = group_values(rows, "strict_trainview_consistency", "mIoU")
    scenes = sorted(baseline, key=lambda scene: np.mean(list(ipr[scene].values())) - np.mean(list(baseline[scene].values())))
    label_map = {
        "bed": "Bed", "bench": "Bench", "blue_sofa": "Blue sofa",
        "covered_desk": "Covered desk", "lawn": "Lawn",
        "office_desk": "Office desk", "room": "Room", "snacks": "Snacks",
        "sofa": "Sofa", "table": "Table",
    }
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 96 * MM), sharey=True)

    for ax, metric, title in zip(axes, ("mIoU", "mBIoU"), ("Region accuracy", "Boundary accuracy")):
        control = group_values(rows, "official", metric)
        treatment = group_values(rows, "strict_trainview_consistency", metric)
        y = np.arange(len(scenes))
        means_control = np.array([np.mean(list(control[scene].values())) for scene in scenes])
        means_treatment = np.array([np.mean(list(treatment[scene].values())) for scene in scenes])
        ax.hlines(y, means_control, means_treatment, color=LIGHT_GREY, linewidth=1.15, zorder=1)
        ax.scatter(means_control, y, color=BLUE, s=23, marker="o", label="Controlled ILGS", zorder=3)
        ax.scatter(means_treatment, y, color=GREEN, s=25, marker="D", label="+ IPR", zorder=3)
        for yi, x0, x1 in zip(y, means_control, means_treatment):
            delta = x1 - x0
            color = GREEN if delta >= 0 else ACCENT_RED
            ax.text(max(x0, x1) + 0.7, yi, f"{delta:+.1f}", color=color,
                    va="center", ha="left", fontsize=6.3, fontweight="bold")
        ax.axvline(np.mean(means_control), color=BLUE, linewidth=0.7, linestyle=(0, (3, 2)), alpha=0.65)
        ax.axvline(np.mean(means_treatment), color=GREEN, linewidth=0.7, linestyle=(0, (3, 2)), alpha=0.65)
        ax.set_title(title, fontweight="bold", pad=5)
        ax.set_xlabel(f"{metric} (%)")
        ax.set_xlim(57 if metric == "mBIoU" else 64, 102)
        ax.grid(axis="x", color="#E6E6E6", linewidth=0.45, zorder=0)
        ax.tick_params(length=3, color="#555555")
        ax.spines["left"].set_color("#555555")
        ax.spines["bottom"].set_color("#555555")

    axes[0].set_yticks(np.arange(len(scenes)), [label_map[scene] for scene in scenes])
    axes[0].invert_yaxis()
    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.01))
    fig.text(0.5, 0.015, "Numbers show scene-level changes; dashed lines mark the ten-scene means.",
             ha="center", color=MID_GREY, fontsize=6.5)
    fig.subplots_adjust(left=0.16, right=0.97, bottom=0.12, top=0.84, wspace=0.12)
    save_all(fig, output_dir / "fig_exp_3dovs_scene_gains")


def plot_component_ablation(rows, output_dir):
    variants = [
        ("official", "Controlled ILGS"),
        ("strict_trainview_cleanup", "Structure cleanup"),
        ("strict_trainview_cleanup_conf", "Cleanup + pixel confidence"),
        ("strict_trainview_consistency_only", "Cleanup + semantic reliability"),
        ("strict_trainview_large_only", "Cleanup + area prior"),
        ("strict_trainview_consistency", "Full IPR"),
    ]
    scenes = ["ramen", "figurines", "teatime"]
    fig, axes = plt.subplots(1, 2, figsize=(183 * MM, 80 * MM), sharey=True)

    for ax, metric, title in zip(axes, ("mIoU", "mBIoU"), ("Region accuracy", "Boundary accuracy")):
        means, sds = [], []
        for variant, _ in variants:
            grouped = group_values(rows, variant, metric)
            values = seed_macro(grouped, scenes)
            means.append(values.mean())
            sds.append(values.std(ddof=1))
        y = np.arange(len(variants))
        colors = [BLUE, MID_GREY, ORANGE, CATEGORICAL[4], CATEGORICAL_EXTENDED[8], GREEN]
        markers = ["o", "s", "s", "^", "v", "D"]
        ax.hlines(y, min(means) - 0.5, means, color="#E1E1E1", linewidth=1.2, zorder=1)
        for yi, mean, sd, color, marker in zip(y, means, sds, colors, markers):
            ax.errorbar(mean, yi, xerr=sd, color=color, marker=marker,
                        markersize=5.3, markeredgecolor="white", markeredgewidth=0.45,
                        capsize=2.5, linewidth=1.1, zorder=3)
            ax.text(mean + sd + 0.28, yi, f"{mean:.2f}", va="center", ha="left",
                    color=color, fontsize=6.4, fontweight="bold" if yi in (0, len(variants)-1) else "normal")
        ax.set_title(title, fontweight="bold", pad=5)
        ax.set_xlabel(f"Three-scene mean {metric} (%)")
        ax.grid(axis="x", color="#E6E6E6", linewidth=0.45, zorder=0)
        ax.tick_params(length=3, color="#555555")
        ax.spines["left"].set_color("#555555")
        ax.spines["bottom"].set_color("#555555")
        ax.set_xlim(63 if metric == "mBIoU" else 67.5, 79)
    axes[0].set_yticks(np.arange(len(variants)), [label for _, label in variants])
    axes[0].invert_yaxis()
    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    fig.subplots_adjust(left=0.27, right=0.98, bottom=0.17, top=0.85, wspace=0.16)
    save_all(fig, output_dir / "fig_exp_component_ablation")


def plot_threshold_sensitivity(lerf_rows, ovs_rows, output_dir):
    fig, axes = plt.subplots(2, 2, figsize=(183 * MM, 105 * MM), sharex=True)
    datasets = [("LERF-Mask", lerf_rows), ("3D-OVS", ovs_rows)]
    metrics = [("mean_mIoU", "mIoU (%)"), ("mean_mBIoU", "mBIoU (%)")]

    for row_index, (dataset_name, rows) in enumerate(datasets):
        thresholds = np.array([float(row["threshold"]) for row in rows])
        order = np.argsort(thresholds)
        thresholds = thresholds[order]
        for col_index, (metric, ylabel) in enumerate(metrics):
            ax = axes[row_index, col_index]
            values = np.array([float(row[metric]) for row in rows])[order]
            color = ORANGE if dataset_name == "LERF-Mask" else GREEN
            ax.plot(thresholds, values, color=color, linewidth=1.35,
                    marker="o", markersize=4.2, markeredgecolor="white", markeredgewidth=0.45)
            selected_index = int(np.where(np.isclose(thresholds, 0.75))[0][0])
            ax.scatter([0.75], [values[selected_index]], s=42, facecolor="white",
                       edgecolor=ACCENT_RED, linewidth=1.25, zorder=4)
            ax.axvline(0.75, color=ACCENT_RED, linestyle=(0, (3, 2)), linewidth=0.75, alpha=0.75)
            for x, y in zip(thresholds, values):
                ax.text(x, y + (0.33 if dataset_name == "LERF-Mask" else 0.20),
                        f"{y:.1f}", ha="center", va="bottom", fontsize=5.9, color=MID_GREY)
            ax.set_ylabel(ylabel)
            ax.set_title(f"{dataset_name}: {ylabel[:-4]}", fontweight="bold", pad=5)
            ax.grid(axis="y", color="#E6E6E6", linewidth=0.45, zorder=0)
            ax.tick_params(length=3, color="#555555")
            ax.spines["left"].set_color("#555555")
            ax.spines["bottom"].set_color("#555555")
            ax.margins(y=0.18)
        axes[row_index, 0].text(0.79, 0.95, "selected threshold",
                                transform=axes[row_index, 0].get_xaxis_transform(),
                                color=ACCENT_RED, fontsize=6.1, va="top", ha="left")

    for ax in axes[1]:
        ax.set_xlabel("Semantic-confidence threshold")
        ax.set_xticks([0.65, 0.70, 0.75, 0.80, 0.85])
    for label, ax in zip(("a", "b", "c", "d"), axes.flat):
        panel_label(ax, label)
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.12, top=0.91, hspace=0.48, wspace=0.25)
    save_all(fig, output_dir / "fig_exp_threshold_sensitivity")


def mask_iou(reference, prediction):
    reference = np.asarray(reference) > 127
    prediction = np.asarray(prediction) > 127
    union = np.logical_or(reference, prediction).sum()
    return float(np.logical_and(reference, prediction).sum() / union) if union else 0.0


def overlay_mask(rgb, mask, color="#D6604D"):
    rgb = np.asarray(rgb.convert("RGB"), dtype=np.float32)
    mask = np.asarray(mask) > 127
    grey = np.dot(rgb[..., :3], [0.299, 0.587, 0.114])
    canvas = np.repeat(grey[..., None], 3, axis=2) * 0.72
    tint = np.array(mpl.colors.to_rgb(color), dtype=np.float32) * 255.0
    canvas[mask] = 0.34 * canvas[mask] + 0.66 * tint
    inner = mask.copy()
    inner[1:, :] &= mask[:-1, :]
    inner[:-1, :] &= mask[1:, :]
    inner[:, 1:] &= mask[:, :-1]
    inner[:, :-1] &= mask[:, 1:]
    boundary = mask & ~inner
    canvas[boundary] = np.array([255, 255, 255], dtype=np.float32)
    return np.clip(canvas, 0, 255).astype(np.uint8)


def plot_qualitative_success_examples(qualitative_dir, output_dir):
    rows = read_rows(qualitative_dir / "manifest.csv")
    fig, axes = plt.subplots(len(rows), 4, figsize=(183 * MM, 112 * MM))
    column_titles = ["RGB", "Ground truth", "Controlled ILGS", "Controlled ILGS + IPR"]

    for row_index, row in enumerate(rows):
        rgb = Image.open(qualitative_dir / row["rgb"]).convert("RGB").resize((1008, 756), Image.Resampling.LANCZOS)
        gt = Image.open(qualitative_dir / row["gt"]).convert("L").resize(rgb.size, Image.Resampling.NEAREST)
        baseline = Image.open(qualitative_dir / row["baseline"]).convert("L").resize(rgb.size, Image.Resampling.NEAREST)
        ipr = Image.open(qualitative_dir / row["ipr"]).convert("L").resize(rgb.size, Image.Resampling.NEAREST)
        images = [
            np.asarray(rgb),
            overlay_mask(rgb, gt),
            overlay_mask(rgb, baseline),
            overlay_mask(rgb, ipr),
        ]
        for col_index, (ax, image) in enumerate(zip(axes[row_index], images)):
            ax.imshow(image)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if row_index == 0:
                ax.set_title(column_titles[col_index], fontweight="bold", pad=5)
        axes[row_index, 0].set_ylabel(
            f"{row['display_scene']}\nquery: {row['query']}",
            rotation=0, ha="right", va="center", labelpad=8, fontsize=7,
        )
        axes[row_index, 2].text(
            0.5, -0.08, f"IoU {100 * mask_iou(gt, baseline):.1f}%",
            transform=axes[row_index, 2].transAxes, ha="center", va="top", fontsize=6.2, color=BLUE,
        )
        axes[row_index, 3].text(
            0.5, -0.08, f"IoU {100 * mask_iou(gt, ipr):.1f}%",
            transform=axes[row_index, 3].transAxes, ha="center", va="top", fontsize=6.2, color=GREEN,
        )

    fig.text(0.01, 0.985, "a", fontsize=9, fontweight="bold", va="top", ha="left")
    fig.text(0.5, 0.015, "Real 3D-OVS test views. Identical views and queries are used for both methods.",
             ha="center", color=MID_GREY, fontsize=6.4)
    fig.subplots_adjust(left=0.16, right=0.995, bottom=0.08, top=0.91, wspace=0.035, hspace=0.16)
    save_all(fig, output_dir / "fig_exp_qualitative_success")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--qualitative_dir", type=Path, default=None)
    args = parser.parse_args()

    lerf_ablation = read_rows(args.data_dir / "lerf_ablation_raw.csv")
    ovs_main = read_rows(args.data_dir / "ovs3d_main_raw.csv")
    lerf_threshold = read_rows(args.data_dir / "lerf_threshold.csv")
    ovs_threshold = read_rows(args.data_dir / "ovs3d_threshold.csv")

    plot_lerf_paired(lerf_ablation, args.output_dir)
    plot_3dovs_gains(ovs_main, args.output_dir)
    plot_component_ablation(lerf_ablation, args.output_dir)
    plot_threshold_sensitivity(lerf_threshold, ovs_threshold, args.output_dir)
    if args.qualitative_dir is not None:
        plot_qualitative_success_examples(args.qualitative_dir, args.output_dir)


if __name__ == "__main__":
    main()
