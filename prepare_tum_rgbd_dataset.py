#!/usr/bin/env python3
"""Convert a TUM RGB-D sequence into an ILGS-compatible metric dataset.

The generated dataset keeps the original, registered depth maps and metric
camera poses for the RGB-D-to-grasp bridge, while also writing the COLMAP text
model expected by ILGS.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class TimedPath:
    timestamp: float
    path: str


@dataclass(frozen=True)
class Pose:
    timestamp: float
    translation: np.ndarray
    quaternion_xyzw: np.ndarray


@dataclass(frozen=True)
class Frame:
    rgb: TimedPath
    depth: TimedPath
    pose: Pose


def parse_timed_paths(path: Path) -> list[TimedPath]:
    rows: list[TimedPath] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        timestamp, relative_path = line.split()[:2]
        rows.append(TimedPath(float(timestamp), relative_path))
    if not rows:
        raise ValueError(f"No entries found in {path}")
    return rows


def parse_poses(path: Path) -> list[Pose]:
    rows: list[Pose] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        values = [float(value) for value in line.split()[:8]]
        rows.append(
            Pose(
                timestamp=values[0],
                translation=np.asarray(values[1:4], dtype=np.float64),
                quaternion_xyzw=np.asarray(values[4:8], dtype=np.float64),
            )
        )
    if not rows:
        raise ValueError(f"No poses found in {path}")
    return rows


def nearest_index(sorted_timestamps: np.ndarray, timestamp: float) -> int:
    index = int(np.searchsorted(sorted_timestamps, timestamp))
    if index <= 0:
        return 0
    if index >= len(sorted_timestamps):
        return len(sorted_timestamps) - 1
    before = index - 1
    return before if timestamp - sorted_timestamps[before] <= sorted_timestamps[index] - timestamp else index


def associate_frames(
    rgb_rows: list[TimedPath],
    depth_rows: list[TimedPath],
    poses: list[Pose],
    max_rgb_depth_delta: float,
    max_pose_delta: float,
) -> list[Frame]:
    depth_times = np.asarray([row.timestamp for row in depth_rows])
    pose_times = np.asarray([row.timestamp for row in poses])
    frames: list[Frame] = []
    used_depth: set[int] = set()

    for rgb in rgb_rows:
        depth_index = nearest_index(depth_times, rgb.timestamp)
        pose_index = nearest_index(pose_times, rgb.timestamp)
        if depth_index in used_depth:
            continue
        if abs(depth_rows[depth_index].timestamp - rgb.timestamp) > max_rgb_depth_delta:
            continue
        if abs(poses[pose_index].timestamp - rgb.timestamp) > max_pose_delta:
            continue
        used_depth.add(depth_index)
        frames.append(Frame(rgb=rgb, depth=depth_rows[depth_index], pose=poses[pose_index]))

    if not frames:
        raise ValueError("No RGB/depth/pose triplets passed the timestamp thresholds")
    return frames


def quaternion_xyzw_to_rotation(quaternion: np.ndarray) -> np.ndarray:
    x, y, z, w = quaternion / np.linalg.norm(quaternion)
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def rotation_to_quaternion_wxyz(rotation: np.ndarray) -> np.ndarray:
    trace = float(np.trace(rotation))
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        quaternion = np.asarray(
            [0.25 * scale, (rotation[2, 1] - rotation[1, 2]) / scale,
             (rotation[0, 2] - rotation[2, 0]) / scale,
             (rotation[1, 0] - rotation[0, 1]) / scale]
        )
    else:
        index = int(np.argmax(np.diag(rotation)))
        if index == 0:
            scale = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2
            quaternion = np.asarray(
                [(rotation[2, 1] - rotation[1, 2]) / scale, 0.25 * scale,
                 (rotation[0, 1] + rotation[1, 0]) / scale,
                 (rotation[0, 2] + rotation[2, 0]) / scale]
            )
        elif index == 1:
            scale = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2
            quaternion = np.asarray(
                [(rotation[0, 2] - rotation[2, 0]) / scale,
                 (rotation[0, 1] + rotation[1, 0]) / scale, 0.25 * scale,
                 (rotation[1, 2] + rotation[2, 1]) / scale]
            )
        else:
            scale = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2
            quaternion = np.asarray(
                [(rotation[1, 0] - rotation[0, 1]) / scale,
                 (rotation[0, 2] + rotation[2, 0]) / scale,
                 (rotation[1, 2] + rotation[2, 1]) / scale, 0.25 * scale]
            )
    quaternion /= np.linalg.norm(quaternion)
    if quaternion[0] < 0:
        quaternion *= -1
    return quaternion


def select_frames(frames: list[Frame], count: int) -> list[Frame]:
    if count <= 0 or count >= len(frames):
        return frames
    indices = np.linspace(0, len(frames) - 1, count)
    indices = np.unique(np.rint(indices).astype(np.int64))
    return [frames[int(index)] for index in indices]


def voxel_downsample(
    points: np.ndarray,
    colors: np.ndarray,
    voxel_size: float,
    max_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if voxel_size > 0:
        voxel_indices = np.floor(points / voxel_size).astype(np.int64)
        _, keep = np.unique(voxel_indices, axis=0, return_index=True)
        keep.sort()
        points = points[keep]
        colors = colors[keep]
    if max_points > 0 and len(points) > max_points:
        rng = np.random.default_rng(seed)
        keep = np.sort(rng.choice(len(points), size=max_points, replace=False))
        points = points[keep]
        colors = colors[keep]
    return points, colors


def write_ascii_ply(path: Path, points: np.ndarray, colors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii") as stream:
        stream.write("ply\nformat ascii 1.0\n")
        stream.write(f"element vertex {len(points)}\n")
        stream.write("property float x\nproperty float y\nproperty float z\n")
        stream.write("property float nx\nproperty float ny\nproperty float nz\n")
        stream.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        stream.write("end_header\n")
        for point, color in zip(points, colors):
            stream.write(
                f"{point[0]:.7f} {point[1]:.7f} {point[2]:.7f} "
                f"0 0 0 {int(color[0])} {int(color[1])} {int(color[2])}\n"
            )


def build_initial_point_cloud(
    sequence_dir: Path,
    frames: list[Frame],
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    depth_factor: float,
    pixel_stride: int,
    min_depth: float,
    max_depth: float,
    voxel_size: float,
    max_points: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []

    for frame in frames:
        rgb = np.asarray(Image.open(sequence_dir / frame.rgb.path).convert("RGB"))
        depth = np.asarray(Image.open(sequence_dir / frame.depth.path), dtype=np.float32) / depth_factor
        if depth.shape != rgb.shape[:2]:
            raise ValueError(f"RGB/depth shape mismatch: {frame.rgb.path} vs {frame.depth.path}")

        rows = np.arange(0, depth.shape[0], pixel_stride)
        cols = np.arange(0, depth.shape[1], pixel_stride)
        grid_u, grid_v = np.meshgrid(cols, rows)
        sampled_depth = depth[grid_v, grid_u]
        valid = np.isfinite(sampled_depth) & (sampled_depth >= min_depth) & (sampled_depth <= max_depth)
        z = sampled_depth[valid]
        u = grid_u[valid].astype(np.float32)
        v = grid_v[valid].astype(np.float32)
        points_camera = np.stack(((u - cx) * z / fx, (v - cy) * z / fy, z), axis=1)

        rotation_wc = quaternion_xyzw_to_rotation(frame.pose.quaternion_xyzw)
        points_world = points_camera @ rotation_wc.T + frame.pose.translation
        all_points.append(points_world.astype(np.float32))
        all_colors.append(rgb[grid_v[valid], grid_u[valid]])

    points = np.concatenate(all_points, axis=0)
    colors = np.concatenate(all_colors, axis=0)
    return voxel_downsample(points, colors, voxel_size, max_points, seed)


def copy_or_link(source: Path, destination: Path, use_symlinks: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        destination.unlink()
    if use_symlinks:
        destination.symlink_to(source.resolve())
    else:
        shutil.copy2(source, destination)


def write_colmap_model(
    sparse_dir: Path,
    frames: list[Frame],
    image_names: list[str],
    width: int,
    height: int,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> None:
    sparse_dir.mkdir(parents=True, exist_ok=True)
    (sparse_dir / "cameras.txt").write_text(
        "# Camera list with one line of data per camera:\n"
        "# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
        f"1 PINHOLE {width} {height} {fx:.9f} {fy:.9f} {cx:.9f} {cy:.9f}\n",
        encoding="utf-8",
    )

    lines = [
        "# Image list with two lines of data per image:",
        "# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME",
        "# POINTS2D[] as (X, Y, POINT3D_ID)",
    ]
    for image_id, (frame, image_name) in enumerate(zip(frames, image_names), start=1):
        rotation_wc = quaternion_xyzw_to_rotation(frame.pose.quaternion_xyzw)
        rotation_cw = rotation_wc.T
        translation_cw = -rotation_cw @ frame.pose.translation
        quaternion_wxyz = rotation_to_quaternion_wxyz(rotation_cw)
        values = [*quaternion_wxyz.tolist(), *translation_cw.tolist()]
        lines.append(
            f"{image_id} " + " ".join(f"{value:.12g}" for value in values) + f" 1 {image_name}"
        )
        lines.append("")
    (sparse_dir / "images.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (sparse_dir / "points3D.txt").write_text(
        "# 3D point list is stored in points3D.ply for ILGS initialization.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", type=Path, required=True, help="Extracted TUM sequence directory")
    parser.add_argument("--output", type=Path, required=True, help="ILGS-compatible output directory")
    parser.add_argument("--num_frames", type=int, default=60)
    parser.add_argument("--holdout_every", type=int, default=8)
    parser.add_argument("--fx", type=float, default=525.0)
    parser.add_argument("--fy", type=float, default=525.0)
    parser.add_argument("--cx", type=float, default=319.5)
    parser.add_argument("--cy", type=float, default=239.5)
    parser.add_argument("--depth_factor", type=float, default=5000.0)
    parser.add_argument("--max_rgb_depth_delta", type=float, default=0.03)
    parser.add_argument("--max_pose_delta", type=float, default=0.03)
    parser.add_argument("--pixel_stride", type=int, default=4)
    parser.add_argument("--min_depth", type=float, default=0.2)
    parser.add_argument("--max_depth", type=float, default=4.0)
    parser.add_argument("--voxel_size", type=float, default=0.008)
    parser.add_argument("--max_points", type=int, default=300_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--symlink", action="store_true", help="Link source images instead of copying")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    sequence_dir = args.sequence.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()
    required = [sequence_dir / name for name in ("rgb.txt", "depth.txt", "groundtruth.txt")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing TUM metadata: " + ", ".join(missing))
    if output_dir.exists() and any(output_dir.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"Output is not empty: {output_dir}. Use --overwrite to replace generated files.")
        for name in ("images", "images_train", "depth", "object_mask", "sparse"):
            generated_path = output_dir / name
            if generated_path.is_symlink() or generated_path.is_file():
                generated_path.unlink()
            elif generated_path.is_dir():
                shutil.rmtree(generated_path)
        metadata_path = output_dir / "rgbd_metadata.json"
        if metadata_path.exists():
            metadata_path.unlink()

    rgb_rows = parse_timed_paths(sequence_dir / "rgb.txt")
    depth_rows = parse_timed_paths(sequence_dir / "depth.txt")
    poses = parse_poses(sequence_dir / "groundtruth.txt")
    associated = associate_frames(
        rgb_rows,
        depth_rows,
        poses,
        args.max_rgb_depth_delta,
        args.max_pose_delta,
    )
    frames = select_frames(associated, args.num_frames)

    sample_rgb = Image.open(sequence_dir / frames[0].rgb.path)
    width, height = sample_rgb.size
    if (width, height) != (640, 480):
        print(f"[warning] Expected TUM resolution 640x480, got {width}x{height}; verify intrinsics")

    images_dir = output_dir / "images"
    images_train_dir = output_dir / "images_train"
    depth_dir = output_dir / "depth"
    object_mask_dir = output_dir / "object_mask"
    sparse_dir = output_dir / "sparse" / "0"
    for directory in (images_dir, images_train_dir, depth_dir, object_mask_dir, sparse_dir):
        directory.mkdir(parents=True, exist_ok=True)

    image_names: list[str] = []
    train_image_names: list[str] = []
    test_image_names: list[str] = []
    manifest_frames: list[dict[str, object]] = []
    for index, frame in enumerate(frames):
        image_name = f"{index:05d}.png"
        image_names.append(image_name)
        copy_or_link(sequence_dir / frame.rgb.path, images_dir / image_name, args.symlink)
        copy_or_link(sequence_dir / frame.depth.path, depth_dir / image_name, args.symlink)
        is_test = args.holdout_every > 0 and index % args.holdout_every == 0
        if is_test:
            test_image_names.append(image_name)
        else:
            train_image_names.append(image_name)
            train_link = images_train_dir / image_name
            if train_link.exists() or train_link.is_symlink():
                train_link.unlink()
            try:
                train_link.symlink_to(Path("..") / "images" / image_name)
            except OSError:
                shutil.copy2(images_dir / image_name, train_link)
        # ILGS requires this file at camera-loading time. It is deliberately a
        # neutral placeholder and must be replaced by tracked pseudo masks.
        Image.fromarray(np.zeros((height, width), dtype=np.uint8)).save(object_mask_dir / image_name)
        manifest_frames.append(
            {
                "index": index,
                "image": f"images/{image_name}",
                "depth": f"depth/{image_name}",
                "rgb_timestamp": frame.rgb.timestamp,
                "depth_timestamp": frame.depth.timestamp,
                "pose_timestamp": frame.pose.timestamp,
                "translation_world_from_camera_m": frame.pose.translation.tolist(),
                "quaternion_world_from_camera_xyzw": frame.pose.quaternion_xyzw.tolist(),
            }
        )

    write_colmap_model(
        sparse_dir,
        frames,
        image_names,
        width,
        height,
        args.fx,
        args.fy,
        args.cx,
        args.cy,
    )
    points, colors = build_initial_point_cloud(
        sequence_dir,
        frames,
        args.fx,
        args.fy,
        args.cx,
        args.cy,
        args.depth_factor,
        args.pixel_stride,
        args.min_depth,
        args.max_depth,
        args.voxel_size,
        args.max_points,
        args.seed,
    )
    write_ascii_ply(sparse_dir / "points3D.ply", points, colors)

    metadata = {
        "format": "tum_rgbd_ilgs_v1",
        "source_sequence": str(sequence_dir),
        "coordinate_system": "TUM ground-truth world frame; metric meters",
        "camera_model": "PINHOLE",
        "width": width,
        "height": height,
        "intrinsics": {"fx": args.fx, "fy": args.fy, "cx": args.cx, "cy": args.cy},
        "depth_factor": args.depth_factor,
        "depth_unit_m": 1.0 / args.depth_factor,
        "associated_frame_count": len(associated),
        "selected_frame_count": len(frames),
        "train_frame_count": len(train_image_names),
        "test_frame_count": len(test_image_names),
        "holdout_every": args.holdout_every,
        "train_images": train_image_names,
        "test_images": test_image_names,
        "initial_point_count": len(points),
        "object_mask_status": "zero placeholders; replace before ILGS training",
        "frames": manifest_frames,
    }
    (output_dir / "rgbd_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "output": str(output_dir),
        "associated_frames": len(associated),
        "selected_frames": len(frames),
        "initial_points": len(points),
        "depth_unit_m": 1.0 / args.depth_factor,
        "next": "generate tracked object masks, then run ILGS preprocessing",
    }, indent=2))


if __name__ == "__main__":
    main()
