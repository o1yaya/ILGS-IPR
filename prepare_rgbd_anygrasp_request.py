#!/usr/bin/env python3
"""Build a metric AnyGrasp request from ILGS masks and registered RGB-D.

The script rejects single-view semantic false positives by voting in the TUM
world frame, then selects the best supporting RGB-D frame. The final cloud is
kept in that camera's metric frame, which is the coordinate convention used by
depth-based grasp detectors.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


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


def largest_component(mask: np.ndarray) -> np.ndarray:
    try:
        from scipy import ndimage

        labels, count = ndimage.label(mask)
        if count == 0:
            return np.zeros_like(mask, dtype=bool)
        sizes = np.bincount(labels.reshape(-1))
        sizes[0] = 0
        return labels == int(np.argmax(sizes))
    except Exception:
        return mask.astype(bool)


def backproject(depth: np.ndarray, intrinsics: dict, pixel_stride: int = 1):
    height, width = depth.shape
    rows = np.arange(0, height, pixel_stride, dtype=np.int32)
    cols = np.arange(0, width, pixel_stride, dtype=np.int32)
    grid_u, grid_v = np.meshgrid(cols, rows)
    z = depth[grid_v, grid_u]
    x = (grid_u.astype(np.float32) - float(intrinsics["cx"])) * z / float(intrinsics["fx"])
    y = (grid_v.astype(np.float32) - float(intrinsics["cy"])) * z / float(intrinsics["fy"])
    return np.stack((x, y, z), axis=-1), grid_v, grid_u


def voxel_reduce(points, colors, normals, region, voxel_size):
    keys = np.floor(points / voxel_size).astype(np.int64)
    unique_keys, inverse = np.unique(keys, axis=0, return_inverse=True)
    count = np.bincount(inverse).astype(np.float64)

    reduced_points = np.stack(
        [np.bincount(inverse, weights=points[:, axis]) / count for axis in range(3)],
        axis=1,
    ).astype(np.float32)
    reduced_colors = np.stack(
        [np.bincount(inverse, weights=colors[:, axis]) / count for axis in range(3)],
        axis=1,
    ).astype(np.uint8)

    reduced_normals = None
    if normals is not None:
        reduced_normals = np.stack(
            [np.bincount(inverse, weights=normals[:, axis]) / count for axis in range(3)],
            axis=1,
        ).astype(np.float32)
        norm = np.linalg.norm(reduced_normals, axis=1, keepdims=True)
        reduced_normals /= np.maximum(norm, 1e-8)

    reduced_region = None
    if region is not None:
        reduced_region = np.bincount(inverse, weights=region.astype(np.float32)) > 0

    return unique_keys, reduced_points, reduced_colors, reduced_normals, reduced_region


def depth_normals(points_grid: np.ndarray, valid_grid: np.ndarray) -> np.ndarray:
    normals = np.zeros_like(points_grid, dtype=np.float32)
    dx = points_grid[1:-1, 2:] - points_grid[1:-1, :-2]
    dy = points_grid[2:, 1:-1] - points_grid[:-2, 1:-1]
    center_valid = (
        valid_grid[1:-1, 1:-1]
        & valid_grid[1:-1, 2:]
        & valid_grid[1:-1, :-2]
        & valid_grid[2:, 1:-1]
        & valid_grid[:-2, 1:-1]
    )
    values = np.cross(dx, dy)
    norm = np.linalg.norm(values, axis=2, keepdims=True)
    values = values / np.maximum(norm, 1e-8)
    centers = points_grid[1:-1, 1:-1]
    flip = np.sum(values * centers, axis=2) > 0
    values[flip] *= -1
    values[~center_valid] = 0
    normals[1:-1, 1:-1] = values
    return normals


def fit_support_plane(points, threshold, iterations, seed):
    if threshold <= 0 or len(points) < 3:
        return None
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(iterations):
        sample = points[rng.choice(len(points), size=3, replace=False)]
        normal = np.cross(sample[1] - sample[0], sample[2] - sample[0])
        length = float(np.linalg.norm(normal))
        if length < 1e-8:
            continue
        normal /= length
        offset = -float(np.dot(normal, sample[0]))
        distance = np.abs(points @ normal + offset)
        inliers = distance <= threshold
        count = int(inliers.sum())
        if best is None or count > best[0]:
            best = (count, normal, offset, inliers)
    if best is None:
        return None

    inlier_points = points[best[3]]
    center = inlier_points.mean(axis=0)
    _, _, vh = np.linalg.svd(inlier_points - center, full_matrices=False)
    normal = vh[-1].astype(np.float32)
    normal /= max(float(np.linalg.norm(normal)), 1e-8)
    offset = -float(np.dot(normal, center))
    distance = np.abs(points @ normal + offset)
    return normal, offset, distance


def assess_support_plane_filter(
    points,
    object_keep,
    min_points,
    min_keep_ratio,
    min_extent_ratio,
):
    """Reject a plane cleanup that collapses the target's geometry."""
    kept_points = points[object_keep]
    keep_ratio = float(len(kept_points) / max(len(points), 1))
    before_extent = points.max(axis=0) - points.min(axis=0)
    before_diagonal = float(np.linalg.norm(before_extent))
    if len(kept_points):
        after_extent = kept_points.max(axis=0) - kept_points.min(axis=0)
        after_diagonal = float(np.linalg.norm(after_extent))
    else:
        after_extent = np.zeros(3, dtype=np.float32)
        after_diagonal = 0.0
    extent_ratio = after_diagonal / max(before_diagonal, 1e-8)

    rejection_reasons = []
    if len(kept_points) < min_points:
        rejection_reasons.append("too_few_remaining_points")
    if keep_ratio < min_keep_ratio:
        rejection_reasons.append("target_point_retention_too_low")
    if extent_ratio < min_extent_ratio:
        rejection_reasons.append("target_extent_retention_too_low")

    return {
        "accepted": not rejection_reasons,
        "remaining_points": int(len(kept_points)),
        "keep_ratio": keep_ratio,
        "before_bbox_extent_m": before_extent.astype(float).tolist(),
        "after_bbox_extent_m": after_extent.astype(float).tolist(),
        "bbox_diagonal_ratio": float(extent_ratio),
        "rejection_reasons": rejection_reasons,
    }


def assess_plane_match(
    target_normal,
    target_offset,
    scene_normal,
    scene_offset,
    min_normal_alignment,
    max_offset_difference,
):
    """Check that a target-plane hypothesis is also present in the surrounding scene."""
    target_normal = np.asarray(target_normal, dtype=np.float32)
    scene_normal = np.asarray(scene_normal, dtype=np.float32)
    target_normal /= max(float(np.linalg.norm(target_normal)), 1e-8)
    scene_normal /= max(float(np.linalg.norm(scene_normal)), 1e-8)
    if float(np.dot(target_normal, scene_normal)) < 0:
        scene_normal = -scene_normal
        scene_offset = -scene_offset
    normal_alignment = float(np.dot(target_normal, scene_normal))
    offset_difference = abs(float(target_offset) - float(scene_offset))
    accepted = (
        normal_alignment >= min_normal_alignment
        and offset_difference <= max_offset_difference
    )
    return {
        "accepted": bool(accepted),
        "normal_alignment": normal_alignment,
        "offset_difference_m": offset_difference,
        "scene_normal_camera": scene_normal.astype(float).tolist(),
        "scene_offset": float(scene_offset),
        "min_normal_alignment": float(min_normal_alignment),
        "max_offset_difference_m": float(max_offset_difference),
    }


def largest_voxel_component(points, voxel_size):
    if voxel_size <= 0 or len(points) == 0:
        return np.ones(len(points), dtype=bool), 1
    keys = np.floor(points / voxel_size).astype(np.int64)
    cell_to_indices = {}
    for index, key in enumerate(keys):
        cell_to_indices.setdefault(tuple(key.tolist()), []).append(index)
    unseen = set(cell_to_indices)
    offsets = [
        (x, y, z)
        for x in (-1, 0, 1)
        for y in (-1, 0, 1)
        for z in (-1, 0, 1)
        if (x, y, z) != (0, 0, 0)
    ]
    components = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        component = [seed]
        while stack:
            key = stack.pop()
            for offset in offsets:
                neighbor = (
                    key[0] + offset[0],
                    key[1] + offset[1],
                    key[2] + offset[2],
                )
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        components.append(component)
    largest = max(
        components,
        key=lambda component: sum(len(cell_to_indices[key]) for key in component),
    )
    keep_cells = set(largest)
    keep = np.asarray([tuple(key.tolist()) in keep_cells for key in keys], dtype=bool)
    return keep, len(components)


def write_ply(path: Path, points: np.ndarray, colors: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
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


def load_frame(dataset: Path, frame: dict, metadata: dict):
    image_name = Path(frame["image"]).name
    rgb = np.asarray(Image.open(dataset / frame["image"]).convert("RGB"))
    depth = np.asarray(Image.open(dataset / frame["depth"]), dtype=np.float32)
    depth /= float(metadata["depth_factor"])
    rotation_wc = quaternion_xyzw_to_rotation(
        np.asarray(frame["quaternion_world_from_camera_xyzw"], dtype=np.float64)
    )
    translation_wc = np.asarray(
        frame["translation_world_from_camera_m"], dtype=np.float64
    )
    return image_name, rgb, depth, rotation_wc, translation_wc


def expanded_key_set(keys: np.ndarray) -> set[tuple[int, int, int]]:
    offsets = np.asarray(
        [[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)],
        dtype=np.int64,
    )
    result = set()
    for key in keys:
        for offset in offsets:
            result.add(tuple((key + offset).tolist()))
    return result


def build_request(args):
    dataset = Path(args.dataset).expanduser().resolve()
    mask_dir = Path(args.mask_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = json.loads((dataset / "rgbd_metadata.json").read_text(encoding="utf-8"))
    intrinsics = metadata["intrinsics"]
    frame_records = []
    all_keys = []
    all_world_points = []
    all_colors = []

    for frame in metadata["frames"]:
        image_name, rgb, depth, rotation_wc, translation_wc = load_frame(
            dataset, frame, metadata
        )
        mask_path = mask_dir / image_name
        if not mask_path.exists():
            continue
        mask = np.asarray(Image.open(mask_path).convert("L")) >= args.mask_threshold
        mask = largest_component(mask)
        points_grid, grid_v, grid_u = backproject(depth, intrinsics, args.vote_pixel_stride)
        valid_depth = np.isfinite(points_grid[..., 2]) & (points_grid[..., 2] >= args.min_depth) & (
            points_grid[..., 2] <= args.max_depth
        )
        sampled_mask = mask[grid_v, grid_u] & valid_depth
        if int(sampled_mask.sum()) < args.min_mask_pixels:
            continue

        points_camera = points_grid[sampled_mask]
        points_world = points_camera @ rotation_wc.T + translation_wc
        colors = rgb[grid_v[sampled_mask], grid_u[sampled_mask]]
        keys, reduced_points, reduced_colors, _, _ = voxel_reduce(
            points_world.astype(np.float32),
            colors,
            None,
            None,
            args.vote_voxel,
        )
        all_keys.append(keys)
        all_world_points.append(reduced_points)
        all_colors.append(reduced_colors)
        frame_records.append(
            {
                "frame": frame,
                "image_name": image_name,
                "mask": mask,
                "voxel_keys": keys,
                "voxel_points_world": reduced_points,
                "mask_pixels": int(mask.sum()),
            }
        )

    if not frame_records:
        raise RuntimeError("No ILGS masks contained enough valid RGB-D pixels")

    stacked_keys = np.concatenate(all_keys, axis=0)
    stacked_points = np.concatenate(all_world_points, axis=0)
    stacked_colors = np.concatenate(all_colors, axis=0)
    consensus_keys, inverse = np.unique(stacked_keys, axis=0, return_inverse=True)
    votes = np.bincount(inverse)
    counts = votes.astype(np.float64)
    consensus_points = np.stack(
        [np.bincount(inverse, weights=stacked_points[:, axis]) / counts for axis in range(3)],
        axis=1,
    ).astype(np.float32)
    consensus_colors = np.stack(
        [np.bincount(inverse, weights=stacked_colors[:, axis]) / counts for axis in range(3)],
        axis=1,
    ).astype(np.uint8)
    keep = votes >= args.min_target_views
    consensus_keys = consensus_keys[keep]
    consensus_points = consensus_points[keep]
    consensus_colors = consensus_colors[keep]
    consensus_votes = votes[keep]
    if len(consensus_points) < args.min_consensus_points:
        raise RuntimeError(
            f"Only {len(consensus_points)} consensus voxels survived. "
            "Lower --min_target_views or inspect the named ILGS masks."
        )

    accepted_keys = expanded_key_set(consensus_keys)
    best = None
    for record in frame_records:
        inliers = np.asarray(
            [tuple(key.tolist()) in accepted_keys for key in record["voxel_keys"]],
            dtype=bool,
        )
        inlier_count = int(inliers.sum())
        inlier_ratio = inlier_count / max(len(inliers), 1)
        record["inlier_voxels"] = inlier_count
        record["inlier_ratio"] = inlier_ratio
        record["reference_score"] = (
            record["mask_pixels"] * inlier_ratio
            if inlier_ratio >= args.min_reference_inlier_ratio
            else 0.0
        )
        if best is None or record["reference_score"] > best["reference_score"]:
            best = record

    if args.reference_frame:
        requested_name = Path(args.reference_frame).name
        matches = [record for record in frame_records if record["image_name"] == requested_name]
        if not matches:
            raise ValueError(
                f"Requested reference frame {requested_name} is not a valid mask/depth candidate"
            )
        best = matches[0]
        if best["inlier_ratio"] < args.min_reference_inlier_ratio:
            raise ValueError(
                f"Requested reference frame {requested_name} has insufficient 3D consensus "
                f"({best['inlier_ratio']:.3f} < {args.min_reference_inlier_ratio:.3f})"
            )

    frame = best["frame"]
    image_name, rgb, depth, rotation_wc, translation_wc = load_frame(dataset, frame, metadata)
    mask = best["mask"]
    points_grid, grid_v, grid_u = backproject(depth, intrinsics, 1)
    valid_grid = np.isfinite(depth) & (depth >= args.min_depth) & (depth <= args.max_depth)
    normals_grid = depth_normals(points_grid, valid_grid)

    mask_valid = mask & valid_grid
    mask_points_camera = points_grid[mask_valid]
    mask_points_world = mask_points_camera @ rotation_wc.T + translation_wc
    mask_keys = np.floor(mask_points_world / args.vote_voxel).astype(np.int64)
    consensus_inliers = np.asarray(
        [tuple(key.tolist()) in accepted_keys for key in mask_keys], dtype=bool
    )

    raw_target_points = mask_points_camera[consensus_inliers].astype(np.float32)
    raw_target_colors = rgb[mask_valid][consensus_inliers]
    raw_target_normals = normals_grid[mask_valid][consensus_inliers].astype(np.float32)
    valid_normals = np.linalg.norm(raw_target_normals, axis=1) > 0.1
    target_points = raw_target_points[valid_normals]
    target_colors = raw_target_colors[valid_normals]
    target_normals = raw_target_normals[valid_normals]
    if len(target_points) < args.min_consensus_points:
        raise RuntimeError("The selected reference frame has too few consensus target points")

    _, target_points, target_colors, target_normals, _ = voxel_reduce(
        target_points,
        target_colors,
        target_normals,
        None,
        args.target_voxel,
    )

    support_margin = np.asarray(
        [args.margin_xy, args.margin_xy, args.margin_z], dtype=np.float32
    )
    support_min = target_points.min(axis=0) - support_margin
    support_max = target_points.max(axis=0) + support_margin
    support_scene_crop = valid_grid & np.all(
        (points_grid >= support_min) & (points_grid <= support_max), axis=2
    )
    surrounding_scene = support_scene_crop & ~mask
    support_scene_points = points_grid[surrounding_scene].astype(np.float32)
    scene_support_plane = fit_support_plane(
        support_scene_points,
        args.support_plane_threshold,
        args.support_plane_iterations,
        args.seed + 1,
    )

    support_plane = None
    if not args.disable_support_plane:
        support_plane = fit_support_plane(
            target_points,
            args.support_plane_threshold,
            args.support_plane_iterations,
            args.seed,
        )
    support_plane_report = {
        "applied": False,
        "disabled": bool(args.disable_support_plane),
        "detected": support_plane is not None,
        "scene_plane_detected": scene_support_plane is not None,
    }
    raw_geometry_keep = valid_normals.copy()
    if support_plane is not None:
        plane_normal, plane_offset, plane_distance = support_plane
        plane_inliers = plane_distance <= args.support_plane_threshold
        object_keep = plane_distance >= args.support_plane_clearance
        inlier_ratio = float(plane_inliers.mean())
        filter_assessment = assess_support_plane_filter(
            target_points,
            object_keep,
            args.min_consensus_points,
            args.min_support_plane_keep_ratio,
            args.min_support_plane_extent_ratio,
        )
        plane_match = None
        if scene_support_plane is not None:
            scene_plane_normal, scene_plane_offset, _ = scene_support_plane
            plane_match = assess_plane_match(
                plane_normal,
                plane_offset,
                scene_plane_normal,
                scene_plane_offset,
                args.min_support_plane_scene_alignment,
                args.max_support_plane_scene_offset,
            )
        support_plane_report.update(
            {
                "normal_camera": plane_normal.astype(float).tolist(),
                "offset": float(plane_offset),
                "inlier_ratio": inlier_ratio,
                "candidate_filter": filter_assessment,
                "scene_plane_match": plane_match,
            }
        )
        if inlier_ratio < args.min_support_plane_ratio:
            support_plane_report["rejection_reason"] = "insufficient_plane_inliers"
        elif not filter_assessment["accepted"]:
            support_plane_report["rejection_reason"] = "target_geometry_collapse"
        elif plane_match is None or not plane_match["accepted"]:
            support_plane_report["rejection_reason"] = (
                "support_plane_not_confirmed_by_scene"
            )
        else:
            before_plane = len(target_points)
            target_points = target_points[object_keep]
            target_colors = target_colors[object_keep]
            target_normals = target_normals[object_keep]
            raw_plane_distance = np.abs(raw_target_points @ plane_normal + plane_offset)
            raw_geometry_keep &= raw_plane_distance >= args.support_plane_clearance
            support_plane_report = {
                "applied": True,
                "disabled": False,
                "detected": True,
                "normal_camera": plane_normal.astype(float).tolist(),
                "offset": float(plane_offset),
                "inlier_ratio": inlier_ratio,
                "removed_points": int(before_plane - len(target_points)),
                "remaining_points": int(len(target_points)),
                "keep_ratio": filter_assessment["keep_ratio"],
                "bbox_diagonal_ratio": filter_assessment["bbox_diagonal_ratio"],
                "candidate_filter": filter_assessment,
                "scene_plane_match": plane_match,
            }

    component_keep, component_count = largest_voxel_component(
        target_points, args.cluster_voxel
    )
    if int(component_keep.sum()) >= args.min_consensus_points:
        target_points = target_points[component_keep]
        target_colors = target_colors[component_keep]
        target_normals = target_normals[component_keep]
        component_keys = expanded_key_set(
            np.floor(target_points / args.cluster_voxel).astype(np.int64)
        )
        raw_component_keys = np.floor(
            raw_target_points / args.cluster_voxel
        ).astype(np.int64)
        raw_geometry_keep &= np.asarray(
            [tuple(key.tolist()) in component_keys for key in raw_component_keys],
            dtype=bool,
        )
    if len(target_points) < args.min_consensus_points:
        raise RuntimeError("Support-plane cleanup left too few target points")

    scene_grid, scene_v, scene_u = backproject(depth, intrinsics, args.scene_pixel_stride)
    scene_valid = np.isfinite(scene_grid[..., 2]) & (scene_grid[..., 2] >= args.min_depth) & (
        scene_grid[..., 2] <= args.max_depth
    )
    scene_points = scene_grid[scene_valid].astype(np.float32)
    scene_colors = rgb[scene_v[scene_valid], scene_u[scene_valid]]

    target_min = target_points.min(axis=0)
    target_max = target_points.max(axis=0)
    margin = np.asarray([args.margin_xy, args.margin_xy, args.margin_z], dtype=np.float32)
    workspace_min = target_min - margin
    workspace_max = target_max + margin
    crop = np.all((scene_points >= workspace_min) & (scene_points <= workspace_max), axis=1)
    scene_points = scene_points[crop]
    scene_colors = scene_colors[crop]
    if len(scene_points) == 0:
        raise RuntimeError("Reference-frame scene crop is empty")

    try:
        from scipy.spatial import cKDTree

        distance, _ = cKDTree(target_points).query(scene_points, k=1, workers=-1)
        region = distance <= args.region_radius
    except Exception:
        diff = scene_points[:, None, :] - target_points[None, :, :]
        region = np.min(np.sum(diff * diff, axis=2), axis=1) <= args.region_radius ** 2

    _, scene_points, scene_colors, _, region = voxel_reduce(
        scene_points,
        scene_colors,
        None,
        region,
        args.scene_voxel,
    )
    if len(scene_points) > args.max_scene_points:
        rng = np.random.default_rng(args.seed)
        selection = np.sort(
            rng.choice(len(scene_points), size=args.max_scene_points, replace=False)
        )
        scene_points = scene_points[selection]
        scene_colors = scene_colors[selection]
        region = region[selection]

    target_center = 0.5 * (target_min + target_max)
    target_extent = target_max - target_min
    centered_scene = scene_points - target_center
    centered_target = target_points - target_center
    centered_workspace_min = workspace_min - target_center
    centered_workspace_max = workspace_max - target_center

    request_path = output_dir / "anygrasp_sdk_request.npz"
    np.savez_compressed(
        request_path,
        points=centered_scene.astype(np.float32),
        colors=(scene_colors.astype(np.float32) / 255.0),
        region_mask=region.astype(bool),
        target_points=centered_target.astype(np.float32),
        target_normals=target_normals.astype(np.float32),
        target_center=target_center.astype(np.float32),
        target_extent=target_extent.astype(np.float32),
        workspace_min=centered_workspace_min.astype(np.float32),
        workspace_max=centered_workspace_max.astype(np.float32),
        coordinate_mode=np.asarray("centered"),
        approach_steering=np.asarray([], dtype=np.float32),
    )
    np.save(output_dir / "points.npy", centered_scene.astype(np.float32))
    np.save(output_dir / "target_points.npy", centered_target.astype(np.float32))
    np.save(output_dir / "target_normals.npy", target_normals.astype(np.float32))
    np.save(output_dir / "region_mask.npy", region.astype(bool))

    write_ply(output_dir / "scene_crop_camera.ply", scene_points, scene_colors)
    write_ply(output_dir / "target_points_camera.ply", target_points, target_colors)
    vote_color = np.zeros((len(consensus_points), 3), dtype=np.uint8)
    vote_strength = np.clip(
        consensus_votes.astype(np.float32) / max(float(consensus_votes.max()), 1.0), 0, 1
    )
    vote_color[:, 0] = (255 * vote_strength).astype(np.uint8)
    vote_color[:, 1] = (220 * (1 - vote_strength)).astype(np.uint8)
    vote_color[:, 2] = 80
    write_ply(output_dir / "target_consensus_world.ply", consensus_points, vote_color)

    filtered_mask = np.zeros_like(mask, dtype=np.uint8)
    flat_valid_indices = np.flatnonzero(mask_valid)
    consensus_indices = flat_valid_indices[consensus_inliers]
    filtered_mask.reshape(-1)[consensus_indices[raw_geometry_keep]] = 255
    Image.fromarray(filtered_mask).save(output_dir / "selected_target_mask.png")
    overlay = rgb.astype(np.float32)
    selected = filtered_mask > 0
    overlay[selected] = 0.45 * overlay[selected] + 0.55 * np.asarray([0, 210, 220])
    Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)).save(
        output_dir / "selected_frame_overlay.png"
    )

    per_frame = [
        {
            "image": record["image_name"],
            "mask_pixels": record["mask_pixels"],
            "inlier_voxels": record["inlier_voxels"],
            "inlier_ratio": record["inlier_ratio"],
            "reference_score": record["reference_score"],
        }
        for record in frame_records
    ]
    report = {
        "dataset": str(dataset),
        "mask_dir": str(mask_dir),
        "output_dir": str(output_dir),
        "coordinate_system": (
            f"metric camera frame of {image_name}: +x right, +y down, +z forward"
        ),
        "selected_reference_frame": image_name,
        "candidate_frames": len(frame_records),
        "min_target_views": args.min_target_views,
        "consensus_voxels_world": int(len(consensus_points)),
        "target_points": int(len(target_points)),
        "scene_points": int(len(scene_points)),
        "region_points": int(region.sum()),
        "support_plane": support_plane_report,
        "target_component_count": int(component_count),
        "target_center_camera_m": target_center.astype(float).tolist(),
        "target_extent_m": target_extent.astype(float).tolist(),
        "workspace_min_centered_m": centered_workspace_min.astype(float).tolist(),
        "workspace_max_centered_m": centered_workspace_max.astype(float).tolist(),
        "preprocessing_parameters": {
            "mask_threshold": args.mask_threshold,
            "min_mask_pixels": args.min_mask_pixels,
            "min_target_views": args.min_target_views,
            "min_consensus_points": args.min_consensus_points,
            "min_reference_inlier_ratio": args.min_reference_inlier_ratio,
            "vote_pixel_stride": args.vote_pixel_stride,
            "vote_voxel_m": args.vote_voxel,
            "target_voxel_m": args.target_voxel,
            "scene_voxel_m": args.scene_voxel,
            "scene_pixel_stride": args.scene_pixel_stride,
            "region_radius_m": args.region_radius,
            "support_plane_threshold_m": args.support_plane_threshold,
            "support_plane_clearance_m": args.support_plane_clearance,
            "support_plane_iterations": args.support_plane_iterations,
            "min_support_plane_ratio": args.min_support_plane_ratio,
            "min_support_plane_keep_ratio": args.min_support_plane_keep_ratio,
            "min_support_plane_extent_ratio": args.min_support_plane_extent_ratio,
            "min_support_plane_scene_alignment": args.min_support_plane_scene_alignment,
            "max_support_plane_scene_offset_m": args.max_support_plane_scene_offset,
            "support_plane_disabled": bool(args.disable_support_plane),
            "cluster_voxel_m": args.cluster_voxel,
            "margin_xy_m": args.margin_xy,
            "margin_z_m": args.margin_z,
            "min_depth_m": args.min_depth,
            "max_depth_m": args.max_depth,
            "max_scene_points": args.max_scene_points,
            "seed": args.seed,
        },
        "per_frame": per_frame,
        "files": {
            "request": str(request_path),
            "overlay": str(output_dir / "selected_frame_overlay.png"),
            "target_ply": str(output_dir / "target_points_camera.ply"),
            "scene_ply": str(output_dir / "scene_crop_camera.ply"),
            "consensus_world_ply": str(output_dir / "target_consensus_world.ply"),
        },
    }
    (output_dir / "rgbd_anygrasp_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--mask_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--mask_threshold", type=int, default=127)
    parser.add_argument("--min_mask_pixels", type=int, default=100)
    parser.add_argument("--min_target_views", type=int, default=2)
    parser.add_argument("--min_consensus_points", type=int, default=100)
    parser.add_argument(
        "--reference_frame",
        default="",
        help="Optional source image name such as 00059.png; otherwise select automatically.",
    )
    parser.add_argument("--min_reference_inlier_ratio", type=float, default=0.5)
    parser.add_argument("--vote_pixel_stride", type=int, default=2)
    parser.add_argument("--vote_voxel", type=float, default=0.01)
    parser.add_argument("--target_voxel", type=float, default=0.004)
    parser.add_argument("--scene_voxel", type=float, default=0.005)
    parser.add_argument("--scene_pixel_stride", type=int, default=1)
    parser.add_argument("--region_radius", type=float, default=0.02)
    parser.add_argument("--support_plane_threshold", type=float, default=0.008)
    parser.add_argument("--support_plane_clearance", type=float, default=0.012)
    parser.add_argument("--support_plane_iterations", type=int, default=600)
    parser.add_argument("--min_support_plane_ratio", type=float, default=0.25)
    parser.add_argument(
        "--min_support_plane_keep_ratio",
        type=float,
        default=0.20,
        help="Reject plane cleanup when it would retain less than this fraction of target points.",
    )
    parser.add_argument(
        "--min_support_plane_extent_ratio",
        type=float,
        default=0.40,
        help="Reject plane cleanup when the target bbox diagonal would shrink below this ratio.",
    )
    parser.add_argument(
        "--min_support_plane_scene_alignment",
        type=float,
        default=0.90,
        help="Require the target-plane normal to match a plane in the surrounding scene.",
    )
    parser.add_argument(
        "--max_support_plane_scene_offset",
        type=float,
        default=0.03,
        help="Maximum plane-offset difference for surrounding-scene confirmation.",
    )
    parser.add_argument(
        "--disable_support_plane",
        action="store_true",
        help="Keep the complete target geometry when the target itself is planar or cylindrical.",
    )
    parser.add_argument("--cluster_voxel", type=float, default=0.008)
    parser.add_argument("--margin_xy", type=float, default=0.20)
    parser.add_argument("--margin_z", type=float, default=0.12)
    parser.add_argument("--min_depth", type=float, default=0.2)
    parser.add_argument("--max_depth", type=float, default=4.0)
    parser.add_argument("--max_scene_points", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=13)
    return parser.parse_args()


if __name__ == "__main__":
    build_request(parse_args())
