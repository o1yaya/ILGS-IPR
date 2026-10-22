#!/usr/bin/env python3
"""Compare AnyGrasp ablations against one clean reference target cloud."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def parse_method(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected NAME=/path/to/candidate_dir")
    name, path = value.split("=", 1)
    if not name or not path:
        raise argparse.ArgumentTypeError("Expected NAME=/path/to/candidate_dir")
    return name, Path(path).expanduser().resolve()


def resolve_request_dir(candidate_dir: Path):
    candidates = [candidate_dir.parent, candidate_dir]
    for path in candidates:
        if (path / "anygrasp_sdk_request.npz").exists():
            return path
    raise FileNotFoundError(f"Cannot locate request package for {candidate_dir}")


def nearest_target(candidate_centers, target_points):
    delta = candidate_centers[:, None, :] - target_points[None, :, :]
    squared = np.sum(delta * delta, axis=2)
    nearest = np.argmin(squared, axis=1)
    distance = np.sqrt(squared[np.arange(len(candidate_centers)), nearest])
    return distance.astype(np.float32), nearest


def target_geometry_metrics(method_points, reference_points):
    """Measure how much of the clean reference target survives preprocessing."""
    reference_to_method, _ = nearest_target(reference_points, method_points)
    method_extent = method_points.max(axis=0) - method_points.min(axis=0)
    reference_extent = reference_points.max(axis=0) - reference_points.min(axis=0)
    method_diagonal = float(np.linalg.norm(method_extent))
    reference_diagonal = float(np.linalg.norm(reference_extent))
    return {
        "method_target_points": int(len(method_points)),
        "target_point_count_ratio": float(len(method_points) / len(reference_points)),
        "reference_geometry_coverage_5mm": float(
            (reference_to_method <= 0.005).mean()
        ),
        "reference_geometry_coverage_10mm": float(
            (reference_to_method <= 0.010).mean()
        ),
        "target_bbox_extent_m": method_extent.astype(float).tolist(),
        "target_bbox_diagonal_m": method_diagonal,
        "target_bbox_diagonal_ratio": float(
            method_diagonal / max(reference_diagonal, 1e-8)
        ),
    }


def occupied_voxels(points, voxel_size):
    if len(points) == 0:
        return 0
    voxel_indices = np.floor(points / voxel_size).astype(np.int64)
    return int(len(np.unique(voxel_indices, axis=0)))


def evaluate_method(name, candidate_dir, reference_points, reference_normals, plane_normal):
    request_dir = resolve_request_dir(candidate_dir)
    request = np.load(request_dir / "anygrasp_sdk_request.npz", allow_pickle=True)
    method_center = request["target_center"].astype(np.float32)
    method_points = request["target_points"].astype(np.float32) + method_center[None, :]
    geometry = target_geometry_metrics(method_points, reference_points)
    selected_path = candidate_dir / "grasp_candidates_selected.npy"
    raw_path = candidate_dir / "grasp_candidates_raw.npy"
    if not selected_path.exists():
        return {
            "method": name,
            "request_dir": str(request_dir),
            "candidate_dir": str(candidate_dir),
            "raw_candidates": 0,
            "saved_candidates": 0,
            "message": "No saved candidate array was produced",
            **geometry,
        }
    selected = np.load(selected_path).astype(np.float32)
    raw_count = len(np.load(raw_path)) if raw_path.exists() else len(selected)
    if len(selected) == 0 or selected.shape[1] < 16:
        return {
            "method": name,
            "request_dir": str(request_dir),
            "candidate_dir": str(candidate_dir),
            "raw_candidates": int(raw_count),
            "saved_candidates": int(len(selected)),
            "message": "No candidates in GraspNet array format",
            **geometry,
        }

    centers_camera = selected[:, 13:16] + method_center[None, :]
    distance, nearest = nearest_target(centers_camera, reference_points)
    rotations = selected[:, 4:13].reshape(-1, 3, 3)
    approaches = rotations[:, :, 0]
    approaches /= np.maximum(np.linalg.norm(approaches, axis=1, keepdims=True), 1e-8)
    normals = reference_normals[nearest]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-8)
    normal_alignment = np.abs(np.sum(approaches * normals, axis=1))
    plane_alignment = (
        np.abs(approaches @ plane_normal) if plane_normal is not None else None
    )
    scores = selected[:, 0]

    thresholds = (0.01, 0.02, 0.03)
    target_hits = distance <= thresholds[1]
    hit_centers = centers_camera[target_hits]
    hit_unique_voxels_10mm = occupied_voxels(hit_centers, 0.010)
    result = {
        "method": name,
        "request_dir": str(request_dir),
        "candidate_dir": str(candidate_dir),
        **geometry,
        "raw_candidates": int(raw_count),
        "saved_candidates": int(len(selected)),
        "hit_count_10mm": int((distance <= thresholds[0]).sum()),
        "hit_rate_10mm": float((distance <= thresholds[0]).mean()),
        "hit_count_20mm": int((distance <= thresholds[1]).sum()),
        "hit_rate_20mm": float((distance <= thresholds[1]).mean()),
        "hit_count_30mm": int((distance <= thresholds[2]).sum()),
        "hit_rate_30mm": float((distance <= thresholds[2]).mean()),
        "distance_mean_m": float(distance.mean()),
        "distance_median_m": float(np.median(distance)),
        "score_max": float(scores.max()),
        "score_mean": float(scores.mean()),
        "normal_alignment_mean": float(normal_alignment.mean()),
        "target_hit_unique_voxels_10mm": hit_unique_voxels_10mm,
        "target_hit_unique_voxel_rate_10mm": float(
            hit_unique_voxels_10mm / max(int(target_hits.sum()), 1)
        ),
        "support_plane_alignment_mean": (
            float(plane_alignment.mean()) if plane_alignment is not None else None
        ),
        "top1": {
            "score": float(scores[0]),
            "distance_m": float(distance[0]),
            "target_hit_20mm": bool(distance[0] <= 0.02),
            "normal_alignment": float(normal_alignment[0]),
            "support_plane_alignment": (
                float(plane_alignment[0]) if plane_alignment is not None else None
            ),
            "width_m": float(selected[0, 1]),
        },
    }
    return result


def main(args):
    reference_dir = Path(args.reference_request).expanduser().resolve()
    reference = np.load(reference_dir / "anygrasp_sdk_request.npz", allow_pickle=True)
    reference_center = reference["target_center"].astype(np.float32)
    reference_points = reference["target_points"].astype(np.float32) + reference_center[None, :]
    reference_normals = reference["target_normals"].astype(np.float32)
    rgbd_report = json.loads(
        (reference_dir / "rgbd_anygrasp_report.json").read_text(encoding="utf-8")
    )
    support_plane = rgbd_report.get("support_plane", {})
    plane_normal = None
    if support_plane.get("applied"):
        plane_normal = np.asarray(support_plane["normal_camera"], dtype=np.float32)
        plane_normal /= max(float(np.linalg.norm(plane_normal)), 1e-8)

    results = [
        evaluate_method(name, path, reference_points, reference_normals, plane_normal)
        for name, path in args.method
    ]
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "reference_request": str(reference_dir),
        "reference_target_points": int(len(reference_points)),
        "primary_hit_threshold_m": 0.02,
        "methods": results,
    }
    (output_dir / "grasp_ablation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    fields = [
        "method", "method_target_points", "target_point_count_ratio",
        "reference_geometry_coverage_5mm", "reference_geometry_coverage_10mm",
        "target_bbox_diagonal_m", "target_bbox_diagonal_ratio",
        "raw_candidates", "saved_candidates", "hit_count_10mm",
        "hit_rate_10mm", "hit_count_20mm", "hit_rate_20mm", "hit_count_30mm",
        "hit_rate_30mm", "distance_mean_m", "distance_median_m", "score_max",
        "score_mean", "normal_alignment_mean", "target_hit_unique_voxels_10mm",
        "target_hit_unique_voxel_rate_10mm", "support_plane_alignment_mean",
    ]
    with (output_dir / "grasp_ablation_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in fields})

    lines = [
        "# AnyGrasp Ablation Summary",
        "",
        "All candidate centers are evaluated against the reference target cloud.",
        "The primary target-hit threshold is 20 mm.",
        "Geometry coverage is the fraction of reference target points within 10 mm of the method target cloud.",
        "",
        "| Method | Target pts | Pts/ref | GeoCov@10mm | Raw/Saved | Hit@20mm | Mean dist. (mm) | Hit voxels@10mm | Max score | Mean normal align. |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        if "hit_rate_20mm" not in result:
            lines.append(
                f"| {result['method']} | {result['method_target_points']} | "
                f"{100 * result['target_point_count_ratio']:.1f}% | "
                f"{100 * result['reference_geometry_coverage_10mm']:.1f}% | "
                f"{result['raw_candidates']}/{result['saved_candidates']} | - | - | - | - | - |"
            )
            continue
        lines.append(
            f"| {result['method']} | {result['method_target_points']} | "
            f"{100 * result['target_point_count_ratio']:.1f}% | "
            f"{100 * result['reference_geometry_coverage_10mm']:.1f}% | "
            f"{result['raw_candidates']}/{result['saved_candidates']} | "
            f"{100 * result['hit_rate_20mm']:.1f}% | "
            f"{1000 * result['distance_mean_m']:.2f} | "
            f"{result['target_hit_unique_voxels_10mm']} | "
            f"{result['score_max']:.4f} | {result['normal_alignment_mean']:.3f} |"
        )
    (output_dir / "grasp_ablation_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference_request", required=True)
    parser.add_argument("--method", action="append", type=parse_method, required=True)
    parser.add_argument("--output_dir", required=True)
    main(parser.parse_args())
