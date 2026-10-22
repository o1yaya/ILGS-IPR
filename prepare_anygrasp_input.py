import argparse
import json
from pathlib import Path

import numpy as np


def read_json(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_ply_xyz_rgb(path):
    from plyfile import PlyData

    ply = PlyData.read(str(path))
    vertices = ply["vertex"].data
    names = vertices.dtype.names or ()
    xyz = np.stack([vertices["x"], vertices["y"], vertices["z"]], axis=1).astype(np.float32)

    if {"red", "green", "blue"}.issubset(set(names)):
        rgb = np.stack([vertices["red"], vertices["green"], vertices["blue"]], axis=1).astype(np.uint8)
    else:
        rgb = np.full((len(xyz), 3), 200, dtype=np.uint8)

    finite = np.isfinite(xyz).all(axis=1)
    return xyz[finite], rgb[finite]


def read_ply_xyz_rgb_normals(path):
    from plyfile import PlyData

    ply = PlyData.read(str(path))
    vertices = ply["vertex"].data
    names = vertices.dtype.names or ()
    xyz = np.stack([vertices["x"], vertices["y"], vertices["z"]], axis=1).astype(np.float32)

    if {"red", "green", "blue"}.issubset(set(names)):
        rgb = np.stack([vertices["red"], vertices["green"], vertices["blue"]], axis=1).astype(np.uint8)
    else:
        rgb = np.full((len(xyz), 3), 200, dtype=np.uint8)

    if {"nx", "ny", "nz"}.issubset(set(names)):
        normals = np.stack([vertices["nx"], vertices["ny"], vertices["nz"]], axis=1).astype(np.float32)
    else:
        normals = np.zeros_like(xyz, dtype=np.float32)

    finite = np.isfinite(xyz).all(axis=1) & np.isfinite(normals).all(axis=1)
    return xyz[finite], rgb[finite], normals[finite]


def write_points_ply(path, points, colors=None, normals=None):
    from plyfile import PlyData, PlyElement

    points = np.asarray(points, dtype=np.float32)
    if colors is None:
        colors = np.full((len(points), 3), 200, dtype=np.uint8)
    else:
        colors = np.asarray(colors)
        if colors.dtype != np.uint8:
            colors = np.clip(colors * 255.0 if colors.max() <= 1.0 else colors, 0, 255).astype(np.uint8)

    if normals is None:
        normals = np.zeros_like(points, dtype=np.float32)
    else:
        normals = np.asarray(normals, dtype=np.float32)

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
    ]
    rows = np.empty(len(points), dtype=dtype)
    rows["x"], rows["y"], rows["z"] = points[:, 0], points[:, 1], points[:, 2]
    rows["nx"], rows["ny"], rows["nz"] = normals[:, 0], normals[:, 1], normals[:, 2]
    rows["red"], rows["green"], rows["blue"] = colors[:, 0], colors[:, 1], colors[:, 2]

    path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(rows, "vertex")]).write(str(path))


def bbox_from_points(points):
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = 0.5 * (mins + maxs)
    extent = maxs - mins
    return mins, maxs, center, extent


def expand_bbox(mins, maxs, margin_ratio, min_margin):
    extent = maxs - mins
    margin = np.maximum(extent * float(margin_ratio), float(min_margin))
    return mins - margin, maxs + margin, margin


def crop_points(points, colors, mins, maxs):
    keep = np.all((points >= mins[None, :]) & (points <= maxs[None, :]), axis=1)
    return points[keep], colors[keep], keep


def random_downsample(points, *arrays, max_points, seed):
    if max_points <= 0 or len(points) <= max_points:
        return (points, *arrays)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(points), size=int(max_points), replace=False)
    return (points[idx], *[arr[idx] for arr in arrays])


def voxel_downsample(points, colors=None, normals=None, voxel_size=0.0):
    if voxel_size <= 0 or len(points) == 0:
        outputs = [points]
        if colors is not None:
            outputs.append(colors)
        if normals is not None:
            outputs.append(normals)
        return tuple(outputs)

    keys = np.floor(points / float(voxel_size)).astype(np.int64)
    _, unique_idx, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    order = np.argsort(unique_idx)
    unique_labels = np.arange(len(unique_idx))[order]

    ds_points = np.zeros((len(unique_idx), 3), dtype=np.float32)
    ds_colors = None if colors is None else np.zeros((len(unique_idx), 3), dtype=np.float32)
    ds_normals = None if normals is None else np.zeros((len(unique_idx), 3), dtype=np.float32)
    counts = np.bincount(inverse).astype(np.float32)

    for axis in range(3):
        ds_points[:, axis] = np.bincount(inverse, weights=points[:, axis]) / counts
        if colors is not None:
            ds_colors[:, axis] = np.bincount(inverse, weights=colors[:, axis].astype(np.float32)) / counts
        if normals is not None:
            ds_normals[:, axis] = np.bincount(inverse, weights=normals[:, axis]) / counts

    ds_points = ds_points[unique_labels]
    outputs = [ds_points]
    if colors is not None:
        outputs.append(np.clip(ds_colors[unique_labels], 0, 255).astype(np.uint8))
    if normals is not None:
        ds_normals = ds_normals[unique_labels]
        norm = np.linalg.norm(ds_normals, axis=1, keepdims=True)
        outputs.append((ds_normals / np.maximum(norm, 1e-8)).astype(np.float32))
    return tuple(outputs)


def load_target_arrays(export_dir):
    clean_points_npy = export_dir / "target_points_clean.npy"
    clean_normals_npy = export_dir / "target_normals_clean.npy"
    clean_points_ply = export_dir / "target_points_clean.ply"
    raw_points_npy = export_dir / "target_points.npy"
    raw_normals_npy = export_dir / "target_normals.npy"
    raw_points_ply = export_dir / "target_points.ply"

    if clean_points_npy.exists():
        points = np.load(clean_points_npy).astype(np.float32)
        points_source = clean_points_npy
        if clean_normals_npy.exists():
            normals = np.load(clean_normals_npy).astype(np.float32)
            normals_source = clean_normals_npy
        elif clean_points_ply.exists():
            _, _, normals = read_ply_xyz_rgb_normals(clean_points_ply)
            normals_source = clean_points_ply
        else:
            normals = np.zeros_like(points)
            normals_source = None
    elif clean_points_ply.exists():
        points, _, normals = read_ply_xyz_rgb_normals(clean_points_ply)
        points_source = clean_points_ply
        normals_source = clean_points_ply
    elif raw_points_npy.exists():
        points = np.load(raw_points_npy).astype(np.float32)
        points_source = raw_points_npy
        normals = np.load(raw_normals_npy).astype(np.float32) if raw_normals_npy.exists() else np.zeros_like(points)
        normals_source = raw_normals_npy if raw_normals_npy.exists() else None
    elif raw_points_ply.exists():
        points, _, normals = read_ply_xyz_rgb_normals(raw_points_ply)
        points_source = raw_points_ply
        normals_source = raw_points_ply
    else:
        raise FileNotFoundError(f"No target point file found under {export_dir}")

    if len(points) != len(normals):
        raise ValueError(f"Target points/normals length mismatch: {len(points)} vs {len(normals)}")
    return points, normals, points_source, normals_source


def resolve_scene_ply(export_dir, args):
    if args.scene_ply:
        return Path(args.scene_ply).expanduser().resolve()

    bbox = read_json(export_dir / "target_bbox.json") or {}
    point_cloud_path = bbox.get("point_cloud_path")
    if point_cloud_path:
        path = Path(point_cloud_path)
        if path.exists():
            return path

    raise FileNotFoundError(
        "Could not resolve scene point cloud. Pass --scene_ply explicitly, "
        "or keep target_bbox.json with a valid point_cloud_path."
    )


def prepare_anygrasp_input(args):
    export_dir = Path(args.export_dir).expanduser().resolve()
    if not export_dir.exists():
        raise FileNotFoundError(f"Export directory not found: {export_dir}")

    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else export_dir / "grasp_input"
    out_dir.mkdir(parents=True, exist_ok=True)

    target_points, target_normals, target_points_source, target_normals_source = load_target_arrays(export_dir)
    target_points = target_points * float(args.scale)

    target_mins, target_maxs, target_center, target_extent = bbox_from_points(target_points)
    workspace_mins, workspace_maxs, workspace_margin = expand_bbox(
        target_mins,
        target_maxs,
        args.margin_ratio,
        args.min_margin * float(args.scale),
    )

    scene_ply = resolve_scene_ply(export_dir, args)
    scene_points, scene_colors = read_ply_xyz_rgb(scene_ply)
    scene_points = scene_points * float(args.scale)
    scene_crop, scene_crop_colors, _ = crop_points(scene_points, scene_colors, workspace_mins, workspace_maxs)

    if len(scene_crop) == 0:
        raise RuntimeError(
            "Scene crop is empty. Increase --margin_ratio/--min_margin or check coordinate frames."
        )

    target_colors = np.full((len(target_points), 3), [220, 90, 55], dtype=np.uint8)

    if args.target_voxel > 0:
        target_points, target_colors, target_normals = voxel_downsample(
            target_points, target_colors, target_normals, voxel_size=args.target_voxel * float(args.scale)
        )
    if args.scene_voxel > 0:
        scene_crop, scene_crop_colors = voxel_downsample(
            scene_crop, scene_crop_colors, voxel_size=args.scene_voxel * float(args.scale)
        )

    target_points, target_colors, target_normals = random_downsample(
        target_points,
        target_colors,
        target_normals,
        max_points=args.max_target_points,
        seed=args.seed,
    )
    scene_crop, scene_crop_colors = random_downsample(
        scene_crop,
        scene_crop_colors,
        max_points=args.max_scene_points,
        seed=args.seed + 1,
    )

    centered_target = target_points - target_center[None, :]
    centered_scene = scene_crop - target_center[None, :]

    np.save(out_dir / "target_points.npy", target_points.astype(np.float32))
    np.save(out_dir / "target_normals.npy", target_normals.astype(np.float32))
    np.save(out_dir / "scene_crop_points.npy", scene_crop.astype(np.float32))
    np.save(out_dir / "scene_crop_colors.npy", scene_crop_colors.astype(np.uint8))
    np.save(out_dir / "target_points_centered.npy", centered_target.astype(np.float32))
    np.save(out_dir / "scene_crop_points_centered.npy", centered_scene.astype(np.float32))

    np.savez_compressed(
        out_dir / "anygrasp_input.npz",
        target_points=target_points.astype(np.float32),
        target_normals=target_normals.astype(np.float32),
        scene_points=scene_crop.astype(np.float32),
        scene_colors=scene_crop_colors.astype(np.uint8),
        target_points_centered=centered_target.astype(np.float32),
        scene_points_centered=centered_scene.astype(np.float32),
        target_center=target_center.astype(np.float32),
        target_extent=target_extent.astype(np.float32),
        workspace_min=workspace_mins.astype(np.float32),
        workspace_max=workspace_maxs.astype(np.float32),
    )

    write_points_ply(out_dir / "target_points.ply", target_points, target_colors, target_normals)
    write_points_ply(out_dir / "scene_crop_points.ply", scene_crop, scene_crop_colors)

    metadata = {
        "export_dir": str(export_dir),
        "output_dir": str(out_dir),
        "scene_ply": str(scene_ply),
        "target_points_source": str(target_points_source),
        "target_normals_source": str(target_normals_source) if target_normals_source else None,
        "coordinate_note": (
            "Coordinates remain in the ILGS/3DGS reconstruction frame. Use camera/robot calibration "
            "or a metric scale before real robot execution."
        ),
        "scale": float(args.scale),
        "target_points": int(len(target_points)),
        "scene_crop_points": int(len(scene_crop)),
        "target_bbox_min": target_mins.astype(float).tolist(),
        "target_bbox_max": target_maxs.astype(float).tolist(),
        "target_center": target_center.astype(float).tolist(),
        "target_extent": target_extent.astype(float).tolist(),
        "workspace_min": workspace_mins.astype(float).tolist(),
        "workspace_max": workspace_maxs.astype(float).tolist(),
        "workspace_margin": workspace_margin.astype(float).tolist(),
        "files": {
            "anygrasp_npz": str(out_dir / "anygrasp_input.npz"),
            "target_points": str(out_dir / "target_points.npy"),
            "target_normals": str(out_dir / "target_normals.npy"),
            "scene_crop_points": str(out_dir / "scene_crop_points.npy"),
            "target_ply": str(out_dir / "target_points.ply"),
            "scene_crop_ply": str(out_dir / "scene_crop_points.ply"),
        },
    }
    write_json(out_dir / "grasp_input_metadata.json", metadata)
    return metadata


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a generic grasp-input package from an exported ILGS query target. "
            "The output is suitable as an adapter layer before AnyGrasp/GraspNet-style inference."
        )
    )
    parser.add_argument("--export_dir", required=True)
    parser.add_argument("--scene_ply", default="", help="Defaults to point_cloud_path in target_bbox.json")
    parser.add_argument("--output_dir", default="", help="Defaults to <export_dir>/grasp_input")
    parser.add_argument("--scale", type=float, default=1.0, help="Multiply all coordinates by this value")
    parser.add_argument("--margin_ratio", type=float, default=0.35)
    parser.add_argument("--min_margin", type=float, default=0.05)
    parser.add_argument("--target_voxel", type=float, default=0.0)
    parser.add_argument("--scene_voxel", type=float, default=0.0)
    parser.add_argument("--max_target_points", type=int, default=20000)
    parser.add_argument("--max_scene_points", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=13)
    return parser.parse_args()


if __name__ == "__main__":
    result = prepare_anygrasp_input(parse_args())
    print(json.dumps(result, indent=2))
