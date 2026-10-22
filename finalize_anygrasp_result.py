#!/usr/bin/env python3
"""Export one AnyGrasp candidate as a final camera-frame grasp result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from visualize_anygrasp_candidates import gripper_wireframe, write_ply


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(args):
    request_dir = Path(args.request_dir).expanduser().resolve()
    candidates_dir = request_dir / "grasp_candidates"
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else candidates_dir / f"final_rank_{args.rank:02d}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    request = np.load(request_dir / "anygrasp_sdk_request.npz", allow_pickle=True)
    candidates = np.load(candidates_dir / "grasp_candidates_selected.npy").astype(np.float32)
    candidate_records = load_json(candidates_dir / "grasp_candidates.json")
    rgbd_report = load_json(request_dir / "rgbd_anygrasp_report.json")
    if not 0 <= args.rank < len(candidates):
        raise IndexError(f"rank {args.rank} is outside [0, {len(candidates) - 1}]")

    row = candidates[args.rank]
    if len(row) < 16:
        raise ValueError("Candidate does not use the expected GraspNet 17-column format")
    record = candidate_records[args.rank] if args.rank < len(candidate_records) else {}

    score = float(row[0])
    width = float(row[1])
    height = float(row[2])
    depth = float(row[3])
    rotation = row[4:13].reshape(3, 3).astype(np.float32)
    center_centered = row[13:16].astype(np.float32)
    target_center = request["target_center"].astype(np.float32)
    center_camera = center_centered + target_center

    transform_camera_from_grasp = np.eye(4, dtype=np.float32)
    transform_camera_from_grasp[:3, :3] = rotation
    transform_camera_from_grasp[:3, 3] = center_camera
    np.save(output_dir / "T_camera_from_grasp.npy", transform_camera_from_grasp)
    np.savetxt(
        output_dir / "T_camera_from_grasp.txt",
        transform_camera_from_grasp,
        fmt="%.9f",
    )

    target_camera = request["target_points"].astype(np.float32) + target_center[None, :]
    scene_camera = request["points"].astype(np.float32) + target_center[None, :]
    scene_colors = request["colors"].astype(np.float32)
    if (float(np.max(scene_colors)) if scene_colors.size else 0.0) <= 1.0:
        scene_colors *= 255.0
    scene_colors = np.clip(scene_colors * 0.65, 0, 255).astype(np.uint8)
    target_colors = np.tile(np.asarray([0, 220, 225], dtype=np.uint8), (len(target_camera), 1))

    local_gripper = gripper_wireframe(width, height, depth, args.spacing)
    gripper_camera = local_gripper @ rotation.T + center_camera[None, :]
    gripper_colors = np.tile(np.asarray([255, 65, 35], dtype=np.uint8), (len(gripper_camera), 1))
    write_ply(output_dir / "final_gripper_camera.ply", gripper_camera, gripper_colors)
    write_ply(
        output_dir / "scene_target_final_gripper_camera.ply",
        np.concatenate((scene_camera, target_camera, gripper_camera), axis=0),
        np.concatenate((scene_colors, target_colors, gripper_colors), axis=0),
    )

    dataset = Path(rgbd_report["dataset"])
    reference_name = rgbd_report["selected_reference_frame"]
    rgb_path = dataset / "images" / reference_name
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"))
    overlay = rgb.astype(np.float32)
    target_mask_path = request_dir / "selected_target_mask.png"
    if target_mask_path.exists():
        target_mask = np.asarray(Image.open(target_mask_path).convert("L")) > 0
        overlay[target_mask] = (
            0.55 * overlay[target_mask] + 0.45 * np.asarray([0, 220, 225])
        )
    overlay_image = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(overlay_image)

    metadata = load_json(dataset / "rgbd_metadata.json")
    intrinsics = metadata["intrinsics"]
    fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
    cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    in_front = gripper_camera[:, 2] > 1e-5
    projected = gripper_camera[in_front]
    pixels_u = fx * projected[:, 0] / projected[:, 2] + cx
    pixels_v = fy * projected[:, 1] / projected[:, 2] + cy
    for u, v in zip(pixels_u, pixels_v):
        if 0 <= u < overlay_image.width and 0 <= v < overlay_image.height:
            draw.ellipse(
                (u - args.point_radius, v - args.point_radius,
                 u + args.point_radius, v + args.point_radius),
                fill=(255, 55, 25),
            )
    if center_camera[2] > 1e-5:
        center_u = fx * center_camera[0] / center_camera[2] + cx
        center_v = fy * center_camera[1] / center_camera[2] + cy
        radius = 5
        draw.ellipse(
            (center_u - radius, center_v - radius, center_u + radius, center_v + radius),
            outline=(255, 235, 30),
            width=2,
        )
    overlay_image.save(output_dir / "final_grasp_rgb_overlay.png")

    nearest_target_distance = float(
        np.linalg.norm(target_camera - center_camera[None, :], axis=1).min()
    )
    approach_axis = rotation[:, 0]
    closing_axis = rotation[:, 1]
    vertical_axis = rotation[:, 2]
    support_plane = rgbd_report.get("support_plane", {})
    plane_alignment = None
    if support_plane.get("applied"):
        support_normal = np.asarray(support_plane["normal_camera"], dtype=np.float32)
        plane_alignment = float(abs(np.dot(approach_axis, support_normal)))

    final = {
        "rank": int(args.rank),
        "score": score,
        "ranking_score": float(record.get("ranking_score", score)),
        "normal_alignment": record.get("normal_alignment"),
        "support_plane_alignment": plane_alignment,
        "coordinate_system": "reference RGB-D camera frame in meters",
        "reference_frame": reference_name,
        "translation_camera_m": center_camera.astype(float).tolist(),
        "rotation_camera_from_grasp": rotation.astype(float).tolist(),
        "approach_axis_camera": approach_axis.astype(float).tolist(),
        "closing_axis_camera": closing_axis.astype(float).tolist(),
        "vertical_axis_camera": vertical_axis.astype(float).tolist(),
        "width_m": width,
        "height_m": height,
        "depth_m": depth,
        "nearest_target_distance_m": nearest_target_distance,
        "T_camera_from_grasp": transform_camera_from_grasp.astype(float).tolist(),
        "robot_execution_note": (
            "This pose is in the selected RGB-D camera frame. Real execution requires a "
            "calibrated T_robot_from_camera transform and robot-specific reachability checks."
        ),
        "files": {
            "transform_npy": str(output_dir / "T_camera_from_grasp.npy"),
            "transform_txt": str(output_dir / "T_camera_from_grasp.txt"),
            "combined_ply": str(output_dir / "scene_target_final_gripper_camera.ply"),
            "rgb_overlay": str(output_dir / "final_grasp_rgb_overlay.png"),
        },
    }
    (output_dir / "final_grasp_camera.json").write_text(
        json.dumps(final, indent=2), encoding="utf-8"
    )
    print(json.dumps(final, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request_dir", required=True)
    parser.add_argument("--rank", type=int, default=0)
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--spacing", type=float, default=0.0015)
    parser.add_argument("--point_radius", type=int, default=1)
    main(parser.parse_args())
