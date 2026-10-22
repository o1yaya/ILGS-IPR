#!/usr/bin/env python3
"""Audit and visualize AnyGrasp candidates without Open3D.

The output PLY files contain densely sampled gripper wireframes, so they can be
opened directly in CloudCompare together with the RGB-D scene and target.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def write_ply(path: Path, points: np.ndarray, colors: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colors = np.clip(colors, 0, 255).astype(np.uint8)
    with path.open("w", encoding="ascii") as stream:
        stream.write("ply\nformat ascii 1.0\n")
        stream.write(f"element vertex {len(points)}\n")
        stream.write("property float x\nproperty float y\nproperty float z\n")
        stream.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        stream.write("end_header\n")
        for point, color in zip(points, colors):
            stream.write(
                f"{point[0]:.7f} {point[1]:.7f} {point[2]:.7f} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )


def sample_segment(start, end, spacing):
    length = float(np.linalg.norm(end - start))
    count = max(2, int(np.ceil(length / spacing)) + 1)
    alpha = np.linspace(0.0, 1.0, count, dtype=np.float32)[:, None]
    return start[None, :] * (1.0 - alpha) + end[None, :] * alpha


def gripper_wireframe(width, height, depth, spacing):
    width = max(float(width), 0.005)
    height = max(float(height), 0.005)
    depth = max(float(depth), 0.015)
    back = -0.025
    front = depth
    half_width = width / 2.0
    half_height = height / 2.0

    segments = []
    for z in (-half_height, half_height):
        segments.extend(
            [
                (np.array([back, -half_width, z]), np.array([back, half_width, z])),
                (np.array([back, -half_width, z]), np.array([front, -half_width, z])),
                (np.array([back, half_width, z]), np.array([front, half_width, z])),
            ]
        )
    for x in (back, front):
        for y in (-half_width, half_width):
            segments.append(
                (np.array([x, y, -half_height]), np.array([x, y, half_height]))
            )
    segments.append((np.array([back - 0.025, 0.0, 0.0]), np.array([front, 0.0, 0.0])))
    return np.concatenate(
        [sample_segment(start, end, spacing) for start, end in segments], axis=0
    ).astype(np.float32)


def rank_color(rank, count):
    fraction = rank / max(count - 1, 1)
    return np.asarray(
        [255, int(70 + 170 * fraction), int(40 + 80 * fraction)], dtype=np.uint8
    )


def load_records(path: Path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def main(args):
    request_dir = Path(args.request_dir).expanduser().resolve()
    candidates_dir = (
        Path(args.candidates_dir).expanduser().resolve()
        if args.candidates_dir
        else request_dir / "grasp_candidates"
    )
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else candidates_dir / "visualization"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    request = np.load(request_dir / "anygrasp_sdk_request.npz", allow_pickle=True)
    candidates = np.load(candidates_dir / "grasp_candidates_selected.npy").astype(np.float32)
    records = load_records(candidates_dir / "grasp_candidates.json")

    target_center = request["target_center"].astype(np.float32)
    scene_centered = request["points"].astype(np.float32)
    target_centered = request["target_points"].astype(np.float32)
    scene_camera = scene_centered + target_center[None, :]
    target_camera = target_centered + target_center[None, :]
    scene_colors = request["colors"]
    if (float(np.max(scene_colors)) if scene_colors.size else 0.0) <= 1.0:
        scene_colors = scene_colors * 255.0
    scene_colors = np.clip(scene_colors * 0.65, 0, 255).astype(np.uint8)
    target_colors = np.tile(np.asarray([0, 220, 225], dtype=np.uint8), (len(target_camera), 1))

    all_gripper_points = []
    all_gripper_colors = []
    audit = []
    target_min = target_camera.min(axis=0)
    target_max = target_camera.max(axis=0)

    for rank, row in enumerate(candidates):
        if len(row) < 16:
            continue
        width = float(row[1])
        height = float(row[2])
        depth = float(row[3])
        rotation = row[4:13].reshape(3, 3)
        center_centered = row[13:16]
        center_camera = center_centered + target_center
        local = gripper_wireframe(width, height, depth, args.spacing)
        gripper_camera = local @ rotation.T + center_camera[None, :]
        color = rank_color(rank, len(candidates))
        colors = np.tile(color, (len(gripper_camera), 1))
        all_gripper_points.append(gripper_camera)
        all_gripper_colors.append(colors)
        write_ply(output_dir / f"gripper_rank_{rank:02d}_camera.ply", gripper_camera, colors)

        distances = np.linalg.norm(target_camera - center_camera[None, :], axis=1)
        nearest_distance = float(distances.min())
        inside_expanded_bbox = bool(
            np.all(center_camera >= target_min - args.center_margin)
            and np.all(center_camera <= target_max + args.center_margin)
        )
        source = records[rank] if rank < len(records) else {}
        audit.append(
            {
                "rank": rank,
                "score": float(source.get("score", row[0])),
                "ranking_score": float(source.get("ranking_score", row[0])),
                "normal_alignment": source.get("normal_alignment"),
                "width_m": width,
                "height_m": height,
                "depth_m": depth,
                "center_camera_m": center_camera.astype(float).tolist(),
                "nearest_target_distance_m": nearest_distance,
                "inside_target_bbox_with_margin": inside_expanded_bbox,
            }
        )

    if not all_gripper_points:
        raise RuntimeError("No grasp rows with the expected 17-column GraspNet format")

    gripper_points = np.concatenate(all_gripper_points, axis=0)
    gripper_colors = np.concatenate(all_gripper_colors, axis=0)
    write_ply(output_dir / "all_grippers_camera.ply", gripper_points, gripper_colors)

    combined_points = np.concatenate((scene_camera, target_camera, gripper_points), axis=0)
    combined_colors = np.concatenate((scene_colors, target_colors, gripper_colors), axis=0)
    write_ply(output_dir / "scene_target_grippers_camera.ply", combined_points, combined_colors)

    valid_center_count = sum(item["inside_target_bbox_with_margin"] for item in audit)
    report = {
        "request_dir": str(request_dir),
        "candidates_dir": str(candidates_dir),
        "output_dir": str(output_dir),
        "candidate_count": len(audit),
        "centers_near_target": int(valid_center_count),
        "center_margin_m": float(args.center_margin),
        "coordinate_system": "reference RGB-D camera frame in meters",
        "color_legend": {
            "scene": "dimmed source RGB",
            "target": "cyan",
            "grippers": "red-to-yellow in rank order",
        },
        "candidates": audit,
        "files": {
            "combined": str(output_dir / "scene_target_grippers_camera.ply"),
            "all_grippers": str(output_dir / "all_grippers_camera.ply"),
        },
    }
    (output_dir / "grasp_visualization_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request_dir", required=True)
    parser.add_argument("--candidates_dir", default="")
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--spacing", type=float, default=0.0015)
    parser.add_argument("--center_margin", type=float, default=0.03)
    main(parser.parse_args())
