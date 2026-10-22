import argparse
import colorsys
import csv
import json
import os
import re
from pathlib import Path

import numpy as np

from utils.system_utils import searchForMaxIteration


def id2rgb(object_id):
    object_id = int(object_id)
    if object_id == 0:
        return np.array([0, 0, 0], dtype=np.uint8)
    h = (object_id * 1.6180339887) % 1.0
    s = 0.5 + (object_id % 2) * 0.5
    r, g, b = colorsys.hls_to_rgb(h, 0.5, s)
    return np.array([int(r * 255), int(g * 255), int(b * 255)], dtype=np.uint8)


def slugify(text):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    slug = slug.strip("._-")
    return slug or "query"


def default_export_root():
    env_root = os.environ.get("ILGS_GRASP_EXPORT_ROOT")
    if env_root:
        return Path(env_root).expanduser()

    windows_large_disk = Path("E:/ILGS_grasp_exports")
    if windows_large_disk.anchor and Path("E:/").exists():
        return windows_large_disk

    server_large_disk = Path("/media/server1/data/cxdata/ILGS_grasp_exports")
    if Path("/media/server1/data/cxdata").exists():
        return server_large_disk

    return None


def resolve_iteration(model_path, iteration):
    if iteration != -1:
        return int(iteration)
    point_cloud_dir = model_path / "point_cloud"
    if not point_cloud_dir.exists():
        raise FileNotFoundError(f"Point-cloud directory not found: {point_cloud_dir}")
    return int(searchForMaxIteration(str(point_cloud_dir)))


def find_query_mask(mask_dir, index, query):
    view_dir = mask_dir / str(index)
    if not view_dir.exists():
        return None

    exact = view_dir / f"{query}.png"
    if exact.exists():
        return exact

    query_key = query.lower().strip()
    for path in view_dir.glob("*.png"):
        if path.stem.lower().strip() == query_key:
            return path
    return None


def collect_query_id_votes(base_path, mask_dir, query, args):
    from PIL import Image

    logits_dir = base_path / "logits"
    if not logits_dir.exists():
        raise FileNotFoundError(f"Rendered logits directory not found: {logits_dir}")

    logit_files = sorted(logits_dir.glob("*_logits.npy"))
    if not logit_files:
        raise FileNotFoundError(f"No *_logits.npy files found under {logits_dir}")

    id_pixel_counts = {}
    view_rows = []
    total_mask_pixels = 0
    found_masks = 0
    skipped_masks = []

    for logit_path in logit_files:
        index = int(logit_path.name.split("_")[0])
        if args.view_indices and index not in args.view_indices:
            continue

        mask_path = find_query_mask(mask_dir, index, query)
        if mask_path is None:
            skipped_masks.append({"index": index, "reason": "missing_mask"})
            continue

        mask = np.array(Image.open(mask_path).convert("L"))
        mask_bool = mask > args.mask_threshold
        mask_pixels = int(mask_bool.sum())
        if mask_pixels < args.min_view_mask_pixels:
            skipped_masks.append(
                {"index": index, "reason": "too_few_mask_pixels", "pixels": mask_pixels}
            )
            continue

        logits = np.load(logit_path).astype(np.int64)
        if logits.shape != mask_bool.shape:
            raise ValueError(
                f"Mask/logits shape mismatch for view {index}: "
                f"{mask_bool.shape} vs {logits.shape}"
            )

        values, counts = np.unique(logits[mask_bool], return_counts=True)
        counts_by_id = {}
        for value, count in zip(values, counts):
            value = int(value)
            count = int(count)
            if value in args.exclude_ids:
                continue
            if args.ignore_background and value == 0:
                continue
            counts_by_id[value] = count
            id_pixel_counts[value] = id_pixel_counts.get(value, 0) + count

        total_mask_pixels += mask_pixels
        found_masks += 1
        view_rows.append(
            {
                "index": index,
                "mask_path": str(mask_path),
                "logits_path": str(logit_path),
                "mask_pixels": mask_pixels,
                "ids": dict(sorted(counts_by_id.items(), key=lambda item: item[1], reverse=True)),
            }
        )

    if found_masks == 0:
        available_queries = []
        for view_dir in sorted(mask_dir.glob("*"))[:5]:
            if view_dir.is_dir():
                available_queries.extend(path.stem for path in sorted(view_dir.glob("*.png"))[:12])
        raise FileNotFoundError(
            f"No usable masks found for query '{query}' under {mask_dir}. "
            f"Example available query names: {sorted(set(available_queries))[:20]}"
        )

    selected = []
    for object_id, count in sorted(id_pixel_counts.items(), key=lambda item: item[1], reverse=True):
        ratio = count / max(1, total_mask_pixels)
        if object_id in args.include_ids:
            selected.append((object_id, count, ratio, "include_ids"))
            continue
        if count < args.min_id_pixels:
            continue
        if ratio < args.min_id_ratio:
            continue
        selected.append((object_id, count, ratio, "vote"))

    for object_id in args.include_ids:
        if object_id not in [item[0] for item in selected]:
            selected.append((object_id, 0, 0.0, "include_ids"))

    if args.max_ids > 0:
        manual = [item for item in selected if item[3] == "include_ids"]
        voted = [item for item in selected if item[3] != "include_ids"]
        selected = manual + voted[: max(0, args.max_ids - len(manual))]

    if not selected:
        vote_preview = [
            {"id": int(object_id), "pixels": int(count), "ratio": count / max(1, total_mask_pixels)}
            for object_id, count in sorted(id_pixel_counts.items(), key=lambda item: item[1], reverse=True)[:20]
        ]
        raise RuntimeError(
            "No object ids passed the selection thresholds. "
            f"Top vote preview: {vote_preview}"
        )

    return {
        "selected_ids": [int(item[0]) for item in selected],
        "selected_rows": [
            {"id": int(item[0]), "pixels": int(item[1]), "ratio": float(item[2]), "source": item[3]}
            for item in selected
        ],
        "all_id_votes": [
            {
                "id": int(object_id),
                "pixels": int(count),
                "ratio": float(count / max(1, total_mask_pixels)),
            }
            for object_id, count in sorted(id_pixel_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "views": view_rows,
        "skipped": skipped_masks,
        "total_mask_pixels": int(total_mask_pixels),
        "usable_view_count": int(found_masks),
    }


def load_vertices_and_classifier(model_path, iteration):
    import torch
    from plyfile import PlyData

    point_cloud_path = model_path / "point_cloud" / f"iteration_{iteration}" / "point_cloud.ply"
    classifier_path = model_path / "point_cloud" / f"iteration_{iteration}" / "classifier.pth"

    if not point_cloud_path.exists():
        raise FileNotFoundError(f"Trained point cloud not found: {point_cloud_path}")
    if not classifier_path.exists():
        raise FileNotFoundError(f"Classifier checkpoint not found: {classifier_path}")

    ply = PlyData.read(str(point_cloud_path))
    vertices = ply["vertex"].data
    names = vertices.dtype.names or ()
    obj_names = sorted(
        [name for name in names if name.startswith("obj_dc_")],
        key=lambda name: int(name.split("_")[-1]),
    )
    if not obj_names:
        raise ValueError(f"No obj_dc_* fields found in {point_cloud_path}")

    objects = np.stack([np.asarray(vertices[name], dtype=np.float32) for name in obj_names], axis=1)
    state = torch.load(str(classifier_path), map_location="cpu")
    weight = state["weight"].detach().cpu().numpy()[:, :, 0, 0]
    bias = state.get("bias")
    bias = bias.detach().cpu().numpy() if bias is not None else np.zeros(weight.shape[0], dtype=np.float32)

    if objects.shape[1] != weight.shape[1]:
        raise ValueError(
            f"Classifier expects {weight.shape[1]} object channels, "
            f"but PLY has {objects.shape[1]} obj_dc_* fields"
        )

    logits = objects @ weight.T + bias
    pred_ids = np.argmax(logits, axis=1).astype(np.int64)
    return ply, vertices, pred_ids, point_cloud_path, classifier_path


def estimate_normals(points, k):
    from scipy.spatial import cKDTree

    if points.shape[0] < 3:
        return np.zeros_like(points, dtype=np.float32)

    k = max(3, min(int(k), points.shape[0]))
    tree = cKDTree(points)
    _, neighbors = tree.query(points, k=k)
    center = points.mean(axis=0)
    normals = np.zeros_like(points, dtype=np.float32)

    for idx, neighbor_ids in enumerate(neighbors):
        local = points[np.atleast_1d(neighbor_ids)]
        local = local - local.mean(axis=0, keepdims=True)
        cov = local.T @ local
        _, vecs = np.linalg.eigh(cov)
        normal = vecs[:, 0]
        outward = points[idx] - center
        if np.dot(normal, outward) < 0:
            normal = -normal
        normals[idx] = normal

    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(norm, 1e-8)
    return normals.astype(np.float32)


def write_points_ply(path, points, pred_ids, normals=None):
    from plyfile import PlyData, PlyElement

    colors = np.stack([id2rgb(object_id) for object_id in pred_ids], axis=0)
    if normals is None:
        normals = np.zeros_like(points, dtype=np.float32)

    dtype = [
        ("x", "f4"),
        ("y", "f4"),
        ("z", "f4"),
        ("nx", "f4"),
        ("ny", "f4"),
        ("nz", "f4"),
        ("red", "u1"),
        ("green", "u1"),
        ("blue", "u1"),
        ("object_id", "i4"),
    ]
    rows = np.empty(points.shape[0], dtype=dtype)
    rows["x"] = points[:, 0]
    rows["y"] = points[:, 1]
    rows["z"] = points[:, 2]
    rows["nx"] = normals[:, 0]
    rows["ny"] = normals[:, 1]
    rows["nz"] = normals[:, 2]
    rows["red"] = colors[:, 0]
    rows["green"] = colors[:, 1]
    rows["blue"] = colors[:, 2]
    rows["object_id"] = pred_ids.astype(np.int32)
    PlyData([PlyElement.describe(rows, "vertex")]).write(str(path))


def save_vote_visuals(base_path, mask_dir, query, selected_ids, output_dir, view_rows, mask_threshold):
    from PIL import Image

    vis_dir = output_dir / "mask_vote_vis"
    vis_dir.mkdir(parents=True, exist_ok=True)
    renders_dir = base_path / "renders"
    logits_dir = base_path / "logits"

    selected_ids = set(int(v) for v in selected_ids)
    for row in view_rows:
        index = int(row["index"])
        mask_path = find_query_mask(mask_dir, index, query)
        logits_path = logits_dir / f"{index:05d}_logits.npy"
        if mask_path is None or not logits_path.exists():
            continue

        mask = np.array(Image.open(mask_path).convert("L")) > mask_threshold
        logits = np.load(logits_path).astype(np.int64)
        selected_mask = np.isin(logits, list(selected_ids))

        mask_rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
        mask_rgb[mask] = np.array([255, 255, 255], dtype=np.uint8)
        selected_rgb = np.zeros((*selected_mask.shape, 3), dtype=np.uint8)
        selected_rgb[selected_mask] = np.array([255, 180, 0], dtype=np.uint8)

        render_path = renders_dir / f"{index:05d}.png"
        if render_path.exists():
            rgb = np.array(Image.open(render_path).convert("RGB"))
            query_overlay = rgb.copy()
            query_overlay[mask] = (0.55 * query_overlay[mask] + np.array([80, 220, 255]) * 0.45).astype(np.uint8)
            selected_overlay = rgb.copy()
            selected_overlay[selected_mask] = (
                0.55 * selected_overlay[selected_mask] + np.array([255, 180, 0]) * 0.45
            ).astype(np.uint8)
            panel = np.concatenate([rgb, query_overlay, selected_overlay], axis=1)
            Image.fromarray(panel).save(vis_dir / f"{index:05d}_rgb_query_selected.png")
        else:
            panel = np.concatenate([mask_rgb, selected_rgb], axis=1)
            Image.fromarray(panel).save(vis_dir / f"{index:05d}_query_selected.png")


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_query_gaussians(args):
    from plyfile import PlyData, PlyElement

    model_path = Path(args.model_path).expanduser().resolve()
    iteration = resolve_iteration(model_path, args.iteration)
    phase = args.phase
    base_path = model_path / phase / f"ours_{iteration}_text"
    mask_dir = Path(args.mask_dir).expanduser().resolve() if args.mask_dir else base_path / args.mask_subdir

    if not base_path.exists():
        raise FileNotFoundError(f"Rendered output directory not found: {base_path}")
    if not mask_dir.exists():
        raise FileNotFoundError(f"Mask directory not found: {mask_dir}")

    vote_info = collect_query_id_votes(base_path, mask_dir, args.query, args)
    selected_ids = set(vote_info["selected_ids"])

    ply, vertices, pred_ids, point_cloud_path, classifier_path = load_vertices_and_classifier(
        model_path, iteration
    )
    selected_mask = np.isin(pred_ids, list(selected_ids))
    selected_count = int(selected_mask.sum())
    if selected_count == 0:
        raise RuntimeError(f"Selected ids {sorted(selected_ids)} matched 0 Gaussians in 3D classifier output")

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    else:
        output_root = Path(args.output_root).expanduser() if args.output_root else default_export_root()
        if output_root is None:
            output_root = model_path / "grasp_exports"
        output_dir = (
            output_root.resolve()
            / slugify(model_path.parent.name)
            / slugify(model_path.name)
            / f"iteration_{iteration}"
            / phase
            / slugify(args.query)
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_vertices = vertices[selected_mask]
    full_ply_path = output_dir / "target_gaussians_full.ply"
    PlyData([PlyElement.describe(selected_vertices, "vertex")], text=ply.text).write(str(full_ply_path))

    xyz = np.stack(
        [
            np.asarray(selected_vertices["x"], dtype=np.float32),
            np.asarray(selected_vertices["y"], dtype=np.float32),
            np.asarray(selected_vertices["z"], dtype=np.float32),
        ],
        axis=1,
    )
    selected_pred_ids = pred_ids[selected_mask]
    normals = None if args.skip_normals else estimate_normals(xyz, args.normal_k)

    np.save(output_dir / "target_points.npy", xyz)
    if normals is not None:
        np.save(output_dir / "target_normals.npy", normals)
    write_points_ply(output_dir / "target_points.ply", xyz, selected_pred_ids, normals=normals)

    mins = xyz.min(axis=0)
    maxs = xyz.max(axis=0)
    center = 0.5 * (mins + maxs)
    extent = maxs - mins

    unique_3d_ids, unique_3d_counts = np.unique(selected_pred_ids, return_counts=True)
    id_rows = [
        {
            "id": int(object_id),
            "gaussians": int(count),
            "ratio": float(count / max(1, selected_count)),
        }
        for object_id, count in sorted(
            zip(unique_3d_ids, unique_3d_counts), key=lambda item: item[1], reverse=True
        )
    ]
    write_csv(output_dir / "selected_id_histogram.csv", id_rows, ["id", "gaussians", "ratio"])

    bbox = {
        "query": args.query,
        "model_path": str(model_path),
        "iteration": int(iteration),
        "phase": phase,
        "base_path": str(base_path),
        "mask_dir": str(mask_dir),
        "point_cloud_path": str(point_cloud_path),
        "classifier_path": str(classifier_path),
        "selected_ids": sorted(int(v) for v in selected_ids),
        "selected_gaussians": selected_count,
        "bbox_min": mins.astype(float).tolist(),
        "bbox_max": maxs.astype(float).tolist(),
        "bbox_center": center.astype(float).tolist(),
        "bbox_extent": extent.astype(float).tolist(),
        "normal_estimation": None
        if args.skip_normals
        else {"method": "knn_pca", "k": int(args.normal_k), "orientation": "outward_from_bbox_center"},
    }
    with (output_dir / "target_bbox.json").open("w", encoding="utf-8") as f:
        json.dump(bbox, f, indent=2)

    with (output_dir / "mask_vote_summary.json").open("w", encoding="utf-8") as f:
        json.dump(vote_info, f, indent=2)

    save_vote_visuals(
        base_path,
        mask_dir,
        args.query,
        selected_ids,
        output_dir,
        vote_info["views"],
        args.mask_threshold,
    )

    return {
        "output_dir": str(output_dir),
        "selected_ids": sorted(int(v) for v in selected_ids),
        "selected_gaussians": selected_count,
        "usable_view_count": vote_info["usable_view_count"],
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Export a language-query target from ILGS rendered masks/logits as a 3D Gaussian subset "
            "for downstream grasp experiments."
        )
    )
    parser.add_argument("-m", "--model_path", required=True, help="ILGS output model directory")
    parser.add_argument("--query", required=True, help="Query name, matching the generated mask filename")
    parser.add_argument("--phase", default="test", choices=["train", "test"], help="Rendered split to read")
    parser.add_argument("--iteration", type=int, default=-1, help="-1 uses the max saved point_cloud iteration")
    parser.add_argument(
        "--mask_subdir",
        default="test_mask",
        help="Mask subdirectory under <model>/<phase>/ours_<iter>_text",
    )
    parser.add_argument("--mask_dir", default="", help="Explicit mask directory override")
    parser.add_argument(
        "--output_root",
        default="",
        help=(
            "Root directory for exports. Defaults to ILGS_GRASP_EXPORT_ROOT, "
            "then E:/ILGS_grasp_exports when available, then the model directory."
        ),
    )
    parser.add_argument("--output_dir", default="", help="Output directory override")
    parser.add_argument("--mask_threshold", type=int, default=127)
    parser.add_argument("--min_view_mask_pixels", type=int, default=20)
    parser.add_argument("--min_id_pixels", type=int, default=50)
    parser.add_argument("--min_id_ratio", type=float, default=0.01)
    parser.add_argument("--max_ids", type=int, default=0, help="0 keeps all ids that pass thresholds")
    parser.add_argument("--include_ids", nargs="*", type=int, default=[])
    parser.add_argument("--exclude_ids", nargs="*", type=int, default=[])
    parser.add_argument("--view_indices", nargs="*", type=int, default=[])
    parser.add_argument("--ignore_background", action="store_true", default=True)
    parser.add_argument("--keep_background", dest="ignore_background", action="store_false")
    parser.add_argument("--skip_normals", action="store_true")
    parser.add_argument("--normal_k", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    result = export_query_gaussians(parse_args())
    print(json.dumps(result, indent=2))
