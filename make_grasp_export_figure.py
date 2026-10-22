import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load_image(path):
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGB"))


def save_image(path, array):
    from PIL import Image

    Image.fromarray(array).save(path)


def split_triptych(image):
    height, width = image.shape[:2]
    panel_w = width // 3
    return [
        image[:, 0:panel_w],
        image[:, panel_w : 2 * panel_w],
        image[:, 2 * panel_w : 3 * panel_w],
    ]


def find_triptych(export_dir, view_index):
    vis_dir = export_dir / "mask_vote_vis"
    if not vis_dir.exists():
        raise FileNotFoundError(f"mask_vote_vis directory not found: {vis_dir}")

    if view_index is not None:
        path = vis_dir / f"{int(view_index):05d}_rgb_query_selected.png"
        if path.exists():
            return path
        raise FileNotFoundError(f"Requested view figure not found: {path}")

    paths = sorted(vis_dir.glob("*_rgb_query_selected.png"))
    if not paths:
        raise FileNotFoundError(f"No *_rgb_query_selected.png files found under {vis_dir}")
    return paths[0]


def read_ply_points(path):
    from plyfile import PlyData

    ply = PlyData.read(str(path))
    vertices = ply["vertex"].data
    names = vertices.dtype.names or ()
    xyz = np.stack([vertices["x"], vertices["y"], vertices["z"]], axis=1).astype(np.float32)

    if {"red", "green", "blue"}.issubset(set(names)):
        colors = np.stack([vertices["red"], vertices["green"], vertices["blue"]], axis=1).astype(np.float32) / 255.0
    else:
        colors = np.full((len(xyz), 3), [0.85, 0.55, 0.18], dtype=np.float32)

    valid = np.isfinite(xyz).all(axis=1)
    return xyz[valid], colors[valid]


def sample_points(points, colors, max_points, seed):
    if len(points) <= max_points:
        return points, colors
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(points), size=max_points, replace=False)
    return points[idx], colors[idx]


def set_axes_equal_3d(ax, points):
    if len(points) == 0:
        return
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    radius = 0.5 * float(np.max(maxs - mins))
    radius = max(radius, 1e-4)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


def draw_point_cloud(ax, points, colors, title, max_points, seed, elev, azim):
    points, colors = sample_points(points, colors, max_points=max_points, seed=seed)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=colors, s=1.0, depthshade=False, linewidths=0)
    set_axes_equal_3d(ax, points)
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=8, pad=4)
    ax.set_xlabel("x", labelpad=-8)
    ax.set_ylabel("y", labelpad=-8)
    ax.set_zlabel("z", labelpad=-8)
    ax.tick_params(labelsize=5, pad=-2)
    ax.grid(False)


def read_json(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_selected_histogram(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_stats(export_dir, raw_points, clean_points):
    clean_report = read_json(export_dir / "clean_report.json") or {}
    vote = read_json(export_dir / "mask_vote_summary.json") or {}
    hist = read_selected_histogram(export_dir / "selected_id_histogram.csv")

    selected_ids = vote.get("selected_ids", [])
    usable_views = vote.get("usable_view_count", None)
    raw_count = int(len(raw_points))
    clean_count = int(len(clean_points)) if clean_points is not None else None
    removed = None if clean_count is None else raw_count - clean_count
    if clean_points is not None and len(clean_points) > 0:
        extent = (clean_points.max(axis=0) - clean_points.min(axis=0)).astype(float).tolist()
    elif raw_points is not None and len(raw_points) > 0:
        extent = (raw_points.max(axis=0) - raw_points.min(axis=0)).astype(float).tolist()
    else:
        extent = None

    lines = []
    if selected_ids:
        lines.append(f"Selected ids: {', '.join(str(v) for v in selected_ids)}")
    if usable_views is not None:
        lines.append(f"Usable views: {usable_views}")
    lines.append(f"Raw points: {raw_count:,}")
    if clean_count is not None:
        lines.append(f"Clean points: {clean_count:,}")
        lines.append(f"Removed: {removed:,}")
    if extent is not None:
        lines.append("Clean cloud extent: " + ", ".join(f"{float(v):.3f}" for v in extent))

    if hist:
        top = hist[:4]
        id_text = "; ".join(
            f"id {row['id']}: {int(float(row['gaussians'])):,}" for row in top if row.get("id")
        )
        if id_text:
            lines.append(f"3D id histogram: {id_text}")

    if clean_report.get("cluster_filter", {}).get("enabled"):
        cluster = clean_report["cluster_filter"]
        lines.append(
            f"Largest component: {cluster.get('largest_component_points', 'n/a'):,} pts, "
            f"eps={float(cluster.get('eps', 0.0)):.4f}"
        )

    return lines


def make_figure(args):
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 7,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "legend.frameon": False,
        }
    )

    export_dir = Path(args.export_dir).expanduser().resolve()
    if not export_dir.exists():
        raise FileNotFoundError(f"Export directory not found: {export_dir}")

    triptych_path = find_triptych(export_dir, args.view_index)
    rgb, query_mask, selected_mask = split_triptych(load_image(triptych_path))

    raw_ply = export_dir / "target_points.ply"
    clean_ply = export_dir / "target_points_clean.ply"
    if not raw_ply.exists():
        raise FileNotFoundError(f"Raw point cloud not found: {raw_ply}")
    if not clean_ply.exists():
        raise FileNotFoundError(f"Clean point cloud not found: {clean_ply}")

    raw_points, raw_colors = read_ply_points(raw_ply)
    clean_points, clean_colors = read_ply_points(clean_ply)
    stats_lines = build_stats(export_dir, raw_points, clean_points)

    fig = plt.figure(figsize=(7.2, 4.8), constrained_layout=False)
    grid = fig.add_gridspec(
        2,
        4,
        width_ratios=[1.05, 1.05, 1.05, 0.95],
        height_ratios=[1.0, 1.05],
        wspace=0.08,
        hspace=0.18,
    )

    image_panels = [
        (rgb, "RGB view"),
        (query_mask, "Language mask"),
        (selected_mask, "Selected Gaussian ids"),
    ]
    panel_letters = ["a", "b", "c"]
    for idx, (image, title) in enumerate(image_panels):
        ax = fig.add_subplot(grid[0, idx])
        ax.imshow(image)
        ax.set_title(title, fontsize=8, pad=4)
        ax.text(
            0.02,
            0.96,
            panel_letters[idx],
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            va="top",
            ha="left",
            color="white",
            bbox=dict(facecolor="black", alpha=0.45, edgecolor="none", pad=1.5),
        )
        ax.set_axis_off()

    ax_stats = fig.add_subplot(grid[0, 3])
    ax_stats.set_axis_off()
    ax_stats.text(0.0, 1.0, "Export summary", fontsize=8, fontweight="bold", va="top")
    ax_stats.text(
        0.0,
        0.88,
        "\n".join(stats_lines),
        fontsize=6.4,
        va="top",
        linespacing=1.35,
        family="monospace",
    )
    ax_stats.text(
        0.0,
        0.08,
        "Language mask -> object ids -> compact target cloud.",
        fontsize=6.6,
        va="bottom",
        color="#333333",
        wrap=True,
    )

    ax_raw = fig.add_subplot(grid[1, 0:2], projection="3d")
    draw_point_cloud(
        ax_raw,
        raw_points,
        raw_colors,
        "Raw exported target cloud",
        args.max_points,
        args.seed,
        args.elev,
        args.azim,
    )
    ax_raw.text2D(0.02, 0.96, "d", transform=ax_raw.transAxes, fontsize=9, fontweight="bold")

    ax_clean = fig.add_subplot(grid[1, 2:4], projection="3d")
    draw_point_cloud(
        ax_clean,
        clean_points,
        clean_colors,
        "Cleaned target cloud",
        args.max_points,
        args.seed + 1,
        args.elev,
        args.azim,
    )
    ax_clean.text2D(0.02, 0.96, "e", transform=ax_clean.transAxes, fontsize=9, fontweight="bold")

    fig.suptitle(args.title, fontsize=9, y=0.985)

    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else export_dir / "paper_figure"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_stem

    outputs = {}
    png_path = out_dir / f"{stem}.png"
    pdf_path = out_dir / f"{stem}.pdf"
    svg_path = out_dir / f"{stem}.svg"
    tiff_path = out_dir / f"{stem}.tiff"

    fig.savefig(png_path, dpi=args.dpi, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    if args.save_tiff:
        fig.savefig(tiff_path, dpi=args.dpi, bbox_inches="tight")
        outputs["tiff"] = str(tiff_path)
    plt.close(fig)

    outputs.update({"png": str(png_path), "pdf": str(pdf_path), "svg": str(svg_path)})

    # Also save the split panels for convenient manual layout in Word/PPT.
    panels_dir = out_dir / "panels"
    panels_dir.mkdir(exist_ok=True)
    save_image(panels_dir / "a_rgb.png", rgb)
    save_image(panels_dir / "b_language_mask.png", query_mask)
    save_image(panels_dir / "c_selected_ids.png", selected_mask)

    report = {
        "export_dir": str(export_dir),
        "triptych": str(triptych_path),
        "raw_ply": str(raw_ply),
        "clean_ply": str(clean_ply),
        "raw_points": int(len(raw_points)),
        "clean_points": int(len(clean_points)),
        "outputs": outputs,
        "stats_lines": stats_lines,
    }
    with (out_dir / f"{stem}_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create a manuscript-style validation figure for an exported ILGS query target: "
            "RGB, language mask, selected object-id mask, raw point cloud, and cleaned point cloud."
        )
    )
    parser.add_argument("--export_dir", required=True)
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--output_stem", default="query_to_grasp_target_figure")
    parser.add_argument("--view_index", type=int, default=None, help="Default: first available diagnostic view")
    parser.add_argument("--title", default="Language-guided target extraction from ILGS")
    parser.add_argument("--max_points", type=int, default=12000)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--elev", type=float, default=20.0)
    parser.add_argument("--azim", type=float, default=-65.0)
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--save_tiff", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    result = make_figure(parse_args())
    print(json.dumps(result, indent=2))
