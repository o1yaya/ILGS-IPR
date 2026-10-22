import argparse
import json
from pathlib import Path

import numpy as np


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_points_ply(path, points, colors):
    points = np.asarray(points, dtype=np.float32)
    colors = np.asarray(colors)
    if colors.dtype != np.uint8:
        colors = np.clip(colors * 255.0 if colors.max() <= 1.0 else colors, 0, 255).astype(np.uint8)

    try:
        from plyfile import PlyData, PlyElement

        rows = np.empty(
            len(points),
            dtype=[
                ("x", "f4"),
                ("y", "f4"),
                ("z", "f4"),
                ("red", "u1"),
                ("green", "u1"),
                ("blue", "u1"),
            ],
        )
        rows["x"], rows["y"], rows["z"] = points[:, 0], points[:, 1], points[:, 2]
        rows["red"], rows["green"], rows["blue"] = colors[:, 0], colors[:, 1], colors[:, 2]
        path.parent.mkdir(parents=True, exist_ok=True)
        PlyData([PlyElement.describe(rows, "vertex")]).write(str(path))
        return
    except ModuleNotFoundError:
        pass

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for point, color in zip(points, colors):
            f.write(
                f"{point[0]:.8f} {point[1]:.8f} {point[2]:.8f} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )


def parse_vec3(text):
    if not text:
        return None
    parts = [float(x.strip()) for x in text.replace(";", ",").split(",") if x.strip()]
    if len(parts) != 3:
        raise ValueError(f"Expected three comma-separated values, got: {text}")
    return np.asarray(parts, dtype=np.float32)


def pairwise_nn_distances(query, reference, chunk_size=65536):
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(reference)
        dist, _ = tree.query(query, k=1, workers=-1)
        return dist.astype(np.float32)
    except Exception:
        distances = np.empty(len(query), dtype=np.float32)
        for start in range(0, len(query), chunk_size):
            end = min(start + chunk_size, len(query))
            chunk = query[start:end]
            diff = chunk[:, None, :] - reference[None, :, :]
            distances[start:end] = np.sqrt(np.min(np.sum(diff * diff, axis=2), axis=1))
        return distances


def estimate_target_spacing(target_points, sample_count=6000):
    if len(target_points) < 2:
        return 0.0
    rng = np.random.default_rng(13)
    if len(target_points) > sample_count:
        target_points = target_points[rng.choice(len(target_points), size=sample_count, replace=False)]
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(target_points)
        dist, _ = tree.query(target_points, k=2, workers=-1)
        nn = dist[:, 1]
    except Exception:
        mins = target_points.min(axis=0)
        maxs = target_points.max(axis=0)
        volume = float(np.prod(np.maximum(maxs - mins, 1e-8)))
        return float((volume / max(len(target_points), 1)) ** (1.0 / 3.0))
    if len(nn) == 0:
        return 0.0
    return float(np.median(nn))


def grid_region_mask(scene_points, target_points, radius):
    voxel = max(float(radius), 1e-8)
    scene_keys = np.floor(scene_points / voxel).astype(np.int64)
    target_keys = np.floor(target_points / voxel).astype(np.int64)
    key_set = set()
    offsets = np.asarray(
        [[dx, dy, dz] for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)],
        dtype=np.int64,
    )
    for key in np.unique(target_keys, axis=0):
        for offset in offsets:
            key_set.add(tuple((key + offset).tolist()))
    return np.asarray([tuple(key.tolist()) in key_set for key in scene_keys], dtype=bool)


def sampled_distance_summary(scene_points, target_points, radius, sample_count=2500):
    if len(scene_points) == 0 or len(target_points) == 0:
        return {"min": None, "median": None, "p95": None}
    rng = np.random.default_rng(17)
    scene_sample = scene_points
    target_sample = target_points
    if len(scene_sample) > sample_count:
        scene_sample = scene_sample[rng.choice(len(scene_sample), size=sample_count, replace=False)]
    if len(target_sample) > sample_count:
        target_sample = target_sample[rng.choice(len(target_sample), size=sample_count, replace=False)]
    distances = pairwise_nn_distances(scene_sample, target_sample)
    return {
        "min": float(distances.min()),
        "median": float(np.median(distances)),
        "p95": float(np.percentile(distances, 95)),
        "note": "sampled approximate distances because scipy.spatial.cKDTree was unavailable",
    }


def make_region_mask(scene_points, target_points, target_extent, radius):
    diag = float(np.linalg.norm(target_extent))
    if radius <= 0:
        spacing = estimate_target_spacing(target_points)
        min_radius = 0.003 * diag
        max_radius = 0.020 * diag
        radius = float(np.clip(2.5 * spacing, min_radius, max_radius))
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(target_points)
        dist, _ = tree.query(scene_points, k=1, workers=-1)
        summary = {
            "min": float(dist.min()),
            "median": float(np.median(dist)),
            "p95": float(np.percentile(dist, 95)),
        }
        return dist <= radius, float(radius), summary
    except Exception:
        mask = grid_region_mask(scene_points, target_points, radius)
        summary = sampled_distance_summary(scene_points, target_points, radius)
        return mask, float(radius), summary


def prepare_request(args):
    grasp_input_dir = Path(args.grasp_input_dir).expanduser().resolve()
    if not grasp_input_dir.exists():
        raise FileNotFoundError(f"grasp_input_dir not found: {grasp_input_dir}")

    metadata_path = grasp_input_dir / "grasp_input_metadata.json"
    metadata = load_json(metadata_path) if metadata_path.exists() else {}

    package = np.load(grasp_input_dir / "anygrasp_input.npz")
    if args.coordinate_mode == "centered":
        scene_points = package["scene_points_centered"].astype(np.float32)
        target_points = package["target_points_centered"].astype(np.float32)
        workspace_min = package["workspace_min"].astype(np.float32) - package["target_center"].astype(np.float32)
        workspace_max = package["workspace_max"].astype(np.float32) - package["target_center"].astype(np.float32)
    else:
        scene_points = package["scene_points"].astype(np.float32)
        target_points = package["target_points"].astype(np.float32)
        workspace_min = package["workspace_min"].astype(np.float32)
        workspace_max = package["workspace_max"].astype(np.float32)

    scene_colors = package["scene_colors"]
    if scene_colors.dtype != np.float32:
        scene_colors_float = scene_colors.astype(np.float32) / 255.0
    else:
        scene_colors_float = scene_colors.astype(np.float32)

    target_normals = package["target_normals"].astype(np.float32)
    target_center = package["target_center"].astype(np.float32)
    target_extent = package["target_extent"].astype(np.float32)
    region_mask, region_radius, scene_to_target_summary = make_region_mask(
        scene_points,
        target_points,
        target_extent,
        float(args.region_radius),
    )

    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else grasp_input_dir / "anygrasp_sdk_request"
    out_dir.mkdir(parents=True, exist_ok=True)

    approach_steering = parse_vec3(args.approach_steering)
    if approach_steering is not None:
        norm = float(np.linalg.norm(approach_steering))
        approach_steering = approach_steering / max(norm, 1e-8)

    np.save(out_dir / "points.npy", scene_points.astype(np.float32))
    np.save(out_dir / "colors.npy", scene_colors_float.astype(np.float32))
    np.save(out_dir / "region_mask.npy", region_mask.astype(bool))
    np.save(out_dir / "target_points.npy", target_points.astype(np.float32))
    np.save(out_dir / "target_normals.npy", target_normals.astype(np.float32))

    np.savez_compressed(
        out_dir / "anygrasp_sdk_request.npz",
        points=scene_points.astype(np.float32),
        colors=scene_colors_float.astype(np.float32),
        region_mask=region_mask.astype(bool),
        target_points=target_points.astype(np.float32),
        target_normals=target_normals.astype(np.float32),
        target_center=target_center.astype(np.float32),
        target_extent=target_extent.astype(np.float32),
        workspace_min=workspace_min.astype(np.float32),
        workspace_max=workspace_max.astype(np.float32),
        coordinate_mode=np.asarray(args.coordinate_mode),
        approach_steering=np.asarray([] if approach_steering is None else approach_steering, dtype=np.float32),
    )

    preview_colors = np.full((len(scene_points), 3), 210, dtype=np.uint8)
    if scene_colors.shape == preview_colors.shape:
        preview_colors = np.clip(scene_colors, 0, 255).astype(np.uint8)
    preview_colors[region_mask] = np.array([232, 88, 58], dtype=np.uint8)
    write_points_ply(out_dir / "points_region_preview.ply", scene_points, preview_colors)

    report = {
        "grasp_input_dir": str(grasp_input_dir),
        "output_dir": str(out_dir),
        "source_metadata": metadata,
        "coordinate_mode": args.coordinate_mode,
        "coordinate_note": (
            "AnyGrasp SDK expects metric camera-frame coordinates. This package preserves the ILGS "
            "reconstruction frame unless --scale and calibration transforms are applied upstream."
        ),
        "points": int(len(scene_points)),
        "target_points": int(len(target_points)),
        "region_points": int(region_mask.sum()),
        "region_ratio": float(region_mask.mean()),
        "region_radius": region_radius,
        "scene_to_target_distance": scene_to_target_summary,
        "workspace_min": workspace_min.astype(float).tolist(),
        "workspace_max": workspace_max.astype(float).tolist(),
        "target_center_world": target_center.astype(float).tolist(),
        "target_extent": target_extent.astype(float).tolist(),
        "approach_steering": None if approach_steering is None else approach_steering.astype(float).tolist(),
        "files": {
            "request_npz": str(out_dir / "anygrasp_sdk_request.npz"),
            "points": str(out_dir / "points.npy"),
            "colors": str(out_dir / "colors.npy"),
            "region_mask": str(out_dir / "region_mask.npy"),
            "preview_ply": str(out_dir / "points_region_preview.ply"),
        },
    }
    write_json(out_dir / "anygrasp_sdk_request_report.json", report)
    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create an AnyGrasp SDK request package from ILGS grasp_input outputs."
    )
    parser.add_argument("--grasp_input_dir", required=True)
    parser.add_argument("--output_dir", default="")
    parser.add_argument(
        "--coordinate_mode",
        choices=["centered", "world"],
        default="centered",
        help="centered is numerically stable; world preserves ILGS coordinates.",
    )
    parser.add_argument(
        "--region_radius",
        type=float,
        default=0.0,
        help="Scene points within this distance to target points become region_steering. <=0 uses auto radius.",
    )
    parser.add_argument(
        "--approach_steering",
        default="",
        help="Optional preferred approach vector, e.g. 0,0,1. Leave empty to disable.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(prepare_request(parse_args()), indent=2))
