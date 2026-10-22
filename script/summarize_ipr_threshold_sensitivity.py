#!/usr/bin/env python3
"""Summarize IPR threshold sensitivity metrics and weighting statistics."""

import argparse
import csv
import json
import re
import statistics
from pathlib import Path


MIOU_RE = re.compile(r"^Overall Mean IoU:\s*([0-9.eE+-]+)\s*$", re.MULTILINE)
MBIOU_RE = re.compile(r"^Overall Boundary Mean IoU:\s*([0-9.eE+-]+)\s*$", re.MULTILINE)


def threshold_code(value):
    return f"{round(float(value) * 100):03d}"


def parse_metrics(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    miou = MIOU_RE.search(text)
    mbiou = MBIOU_RE.search(text)
    if not miou or not mbiou:
        raise ValueError(f"Incomplete evaluation log: {path}")
    return float(miou.group(1)) * 100.0, float(mbiou.group(1)) * 100.0


def parse_weighting_stats(report_dir):
    semantic_path = report_dir / "object_semantics.json"
    summary_path = report_dir / "object_semantic_area_summary.csv"
    data = json.loads(semantic_path.read_text(encoding="utf-8"))
    weights = data.get("object_weights", {})
    reasons = [entry.get("reason", "") for entry in weights.values()]

    total_tracks = len(reasons)
    low_semantic_tracks = sum(reason == "low_semantic_confidence" for reason in reasons)
    large_region_tracks = sum(reason == "large_mixed_region" for reason in reasons)

    total_pixels = 0
    low_confidence_pixels = 0
    with summary_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            total_pixels += int(row["pixels"])
            low_confidence_pixels += int(row["low_confidence_pixels"])

    return {
        "total_tracks": total_tracks,
        "low_semantic_tracks": low_semantic_tracks,
        "large_region_tracks": large_region_tracks,
        "total_pixels": total_pixels,
        "low_confidence_pixels": low_confidence_pixels,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--log_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--scenes", nargs="+", required=True)
    parser.add_argument(
        "--thresholds",
        nargs="+",
        default=["0.65", "0.70", "0.75", "0.80", "0.85"],
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--title", default="IPR threshold sensitivity")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    log_dir = Path(args.log_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for threshold in args.thresholds:
        code = threshold_code(threshold)
        variant = f"strict_trainview_consistency_t{code}"
        for scene in args.scenes:
            log_path = log_dir / f"eval_{scene}_ipr_{variant}_s{args.seed}.txt"
            report_dir = (
                dataset_root
                / scene
                / f"object_mask_ipr_trainview_consistency_t{code}_report"
            )
            if not log_path.is_file():
                raise FileNotFoundError(f"Missing evaluation log: {log_path}")
            if not report_dir.is_dir():
                raise FileNotFoundError(f"Missing threshold report: {report_dir}")

            miou, mbiou = parse_metrics(log_path)
            stats = parse_weighting_stats(report_dir)
            rows.append(
                {
                    "threshold": float(threshold),
                    "scene": scene,
                    "seed": args.seed,
                    "mIoU": miou,
                    "mBIoU": mbiou,
                    **stats,
                }
            )

    raw_path = output_dir / "threshold_sensitivity_raw.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lookup = {(row["threshold"], row["scene"]): row for row in rows}
    summary_rows = []
    for threshold_text in args.thresholds:
        threshold = float(threshold_text)
        values = [lookup[(threshold, scene)] for scene in args.scenes]
        total_tracks = sum(row["total_tracks"] for row in values)
        total_pixels = sum(row["total_pixels"] for row in values)
        summary_rows.append(
            {
                "threshold": threshold,
                "mean_mIoU": statistics.fmean(row["mIoU"] for row in values),
                "mean_mBIoU": statistics.fmean(row["mBIoU"] for row in values),
                "low_semantic_track_ratio": (
                    sum(row["low_semantic_tracks"] for row in values) / total_tracks
                    if total_tracks
                    else 0.0
                ),
                "large_region_track_ratio": (
                    sum(row["large_region_tracks"] for row in values) / total_tracks
                    if total_tracks
                    else 0.0
                ),
                "low_confidence_pixel_ratio": (
                    sum(row["low_confidence_pixels"] for row in values) / total_pixels
                    if total_pixels
                    else 0.0
                ),
            }
        )

    summary_path = output_dir / "threshold_sensitivity_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    lines = [
        f"# {args.title}",
        "",
        f"Seed: {args.seed}. All metric values are percentages.",
        "",
        "| Threshold | "
        + " | ".join(f"{scene} mIoU / mBIoU" for scene in args.scenes)
        + " | Mean mIoU / mBIoU | Low-semantic tracks | Large-region tracks | Low-confidence pixels |",
        "|---:|" + "---:|" * (len(args.scenes) + 4),
    ]
    for summary in summary_rows:
        threshold = summary["threshold"]
        scene_cells = [
            f'{lookup[(threshold, scene)]["mIoU"]:.2f} / '
            f'{lookup[(threshold, scene)]["mBIoU"]:.2f}'
            for scene in args.scenes
        ]
        lines.append(
            f'| {threshold:.2f} | '
            + " | ".join(scene_cells)
            + f' | {summary["mean_mIoU"]:.2f} / {summary["mean_mBIoU"]:.2f}'
            + f' | {summary["low_semantic_track_ratio"] * 100:.1f}%'
            + f' | {summary["large_region_track_ratio"] * 100:.1f}%'
            + f' | {summary["low_confidence_pixel_ratio"] * 100:.1f}% |'
        )

    markdown_path = output_dir / "threshold_sensitivity_summary.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(markdown_path)


if __name__ == "__main__":
    main()
