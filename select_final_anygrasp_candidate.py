#!/usr/bin/env python3
"""Select and export a target-aware final AnyGrasp candidate.

The SDK score measures grasp quality, while the upstream ILGS/RGB-D stage
defines which object should be grasped. This selector combines the existing
normal-guided ranking score with an explicit normal-alignment term plus
target-interior, insertion-depth, and contact terms so that a shallow or
poorly oriented grasp does not win by SDK score alone.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from finalize_anygrasp_result import main as export_final_grasp


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(args):
    request_dir = Path(args.request_dir).expanduser().resolve()
    candidates_dir = request_dir / "grasp_candidates"
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else candidates_dir / "final_selected"
    )

    request = np.load(request_dir / "anygrasp_sdk_request.npz", allow_pickle=True)
    candidates = np.load(candidates_dir / "grasp_candidates_selected.npy").astype(
        np.float32
    )
    records = load_json(candidates_dir / "grasp_candidates.json")
    target_points = request["target_points"].astype(np.float32)
    if len(target_points) == 0:
        raise RuntimeError("The request contains no target points")
    if len(candidates) == 0:
        raise RuntimeError("AnyGrasp produced no selected candidates")

    target_min = target_points.min(axis=0)
    target_max = target_points.max(axis=0)
    bbox_center = 0.5 * (target_min + target_max)
    bbox_half_extent = np.maximum(0.5 * (target_max - target_min), 1e-4)

    audit = []
    limit = min(len(candidates), args.top_n if args.top_n > 0 else len(candidates))
    for rank, row in enumerate(candidates[:limit]):
        if len(row) < 16:
            continue
        record = records[rank] if rank < len(records) else {}
        center = row[13:16]
        relative = (center - bbox_center) / bbox_half_extent
        normalized_radius = float(np.linalg.norm(relative))
        max_axis_offset = float(np.max(np.abs(relative)))
        center_score = float(np.exp(-0.5 * normalized_radius**2))

        nearest_distance = float(
            np.linalg.norm(target_points - center[None, :], axis=1).min()
        )
        contact_score = float(
            np.exp(-0.5 * (nearest_distance / args.contact_scale) ** 2)
        )
        depth = float(row[3])
        depth_score = float(np.clip(depth / args.preferred_depth, 0.0, 1.0))
        width = float(row[1])
        width_fraction = width / max(args.max_gripper_width, 1e-6)
        width_penalty = float(
            np.clip(
                (width_fraction - args.width_penalty_start)
                / max(1.0 - args.width_penalty_start, 1e-6),
                0.0,
                1.0,
            )
        )

        base_score = float(record.get("ranking_score", row[0]))
        normal_alignment_raw = record.get("normal_alignment")
        normal_alignment = (
            float(normal_alignment_raw) if normal_alignment_raw is not None else None
        )
        rejection_reasons = []
        if nearest_distance > args.max_target_distance:
            rejection_reasons.append("target_distance")
        if max_axis_offset > args.max_bbox_offset:
            rejection_reasons.append("bbox_offset")
        if (
            normal_alignment is not None
            and normal_alignment < args.min_normal_alignment
        ):
            rejection_reasons.append("normal_alignment")
        eligible = not rejection_reasons
        selection_score = (
            base_score
            + args.normal_weight * (normal_alignment or 0.0)
            + args.center_weight * center_score
            + args.depth_weight * depth_score
            + args.contact_weight * contact_score
            - args.width_penalty_weight * width_penalty
        )
        if not eligible:
            selection_score = None

        audit.append(
            {
                "rank": rank,
                "eligible": eligible,
                "rejection_reasons": rejection_reasons,
                "selection_score": selection_score,
                "base_ranking_score": base_score,
                "sdk_score": float(row[0]),
                "normal_alignment": normal_alignment,
                "center_score": center_score,
                "depth_score": depth_score,
                "contact_score": contact_score,
                "width_penalty": width_penalty,
                "normalized_center_radius": normalized_radius,
                "max_axis_bbox_offset": max_axis_offset,
                "nearest_target_distance_m": nearest_distance,
                "width_m": width,
                "depth_m": depth,
                "translation_centered_m": center.astype(float).tolist(),
            }
        )

    eligible = [item for item in audit if item["eligible"]]
    if not eligible:
        raise RuntimeError(
            "No candidate passed the target-distance, bbox, and normal checks"
        )
    selected = max(eligible, key=lambda item: item["selection_score"])

    report = {
        "request_dir": str(request_dir),
        "selected_rank": int(selected["rank"]),
        "selection_score": float(selected["selection_score"]),
        "weights": {
            "normal_alignment": args.normal_weight,
            "center": args.center_weight,
            "depth": args.depth_weight,
            "contact": args.contact_weight,
            "width_penalty": args.width_penalty_weight,
        },
        "constraints": {
            "top_n": limit,
            "max_target_distance_m": args.max_target_distance,
            "max_bbox_offset": args.max_bbox_offset,
            "min_normal_alignment": args.min_normal_alignment,
            "preferred_depth_m": args.preferred_depth,
            "max_gripper_width_m": args.max_gripper_width,
        },
        "candidates": sorted(
            audit,
            key=lambda item: (
                item["selection_score"]
                if item["selection_score"] is not None
                else -float("inf")
            ),
            reverse=True,
        ),
    }
    candidates_dir.joinpath("final_selection_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.joinpath("final_selection_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if not args.no_export:
        export_final_grasp(
            SimpleNamespace(
                request_dir=str(request_dir),
                rank=int(selected["rank"]),
                output_dir=str(output_dir),
                spacing=args.spacing,
                point_radius=args.point_radius,
            )
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request_dir", required=True)
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--top_n", type=int, default=20)
    parser.add_argument("--normal_weight", type=float, default=0.10)
    parser.add_argument("--center_weight", type=float, default=0.12)
    parser.add_argument("--depth_weight", type=float, default=0.03)
    parser.add_argument("--contact_weight", type=float, default=0.02)
    parser.add_argument("--width_penalty_weight", type=float, default=0.03)
    parser.add_argument("--preferred_depth", type=float, default=0.03)
    parser.add_argument("--contact_scale", type=float, default=0.01)
    parser.add_argument("--max_target_distance", type=float, default=0.03)
    parser.add_argument("--max_bbox_offset", type=float, default=1.2)
    parser.add_argument("--min_normal_alignment", type=float, default=0.80)
    parser.add_argument("--max_gripper_width", type=float, default=0.08)
    parser.add_argument("--width_penalty_start", type=float, default=0.98)
    parser.add_argument("--spacing", type=float, default=0.0015)
    parser.add_argument("--point_radius", type=int, default=1)
    parser.add_argument("--no_export", action="store_true")
    main(parser.parse_args())
