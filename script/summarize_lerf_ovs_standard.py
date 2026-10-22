#!/usr/bin/env python3
"""Summarize standard LERF-OVS JSON reports across scenes and seeds."""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


STANDARD_SCENES = ["waldo_kitchen", "ramen", "figurines", "teatime"]


def mean_std(values):
    return statistics.fmean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--scenes", nargs="+", default=STANDARD_SCENES)
    parser.add_argument("--methods", nargs="+", default=["official", "ipr"])
    args = parser.parse_args()

    rows = []
    for path in sorted(Path(args.runs_dir).glob("*/summary.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("scene") not in args.scenes or data.get("method") not in args.methods:
            continue
        rows.append(
            {
                "scene": data["scene"],
                "method": data["method"],
                "seed": int(data.get("seed", 0)),
                "n_pairs": int(data["n_pairs"]),
                "missing_predictions": int(data["missing_predictions"]),
                "mIoU": float(data["miou"]) * 100.0,
                "mAcc@0.25": float(data["macc_at_threshold"]) * 100.0,
            }
        )
    if not rows:
        raise SystemExit(f"No standard LERF-OVS reports found under {args.runs_dir}")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "lerf_ovs_standard_raw.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scene"], row["method"])].append(row)
    aggregate = []
    for (scene, method), values in sorted(grouped.items()):
        miou_mean, miou_std = mean_std([row["mIoU"] for row in values])
        macc_mean, macc_std = mean_std([row["mAcc@0.25"] for row in values])
        aggregate.append(
            {
                "scene": scene,
                "method": method,
                "n_seeds": len(values),
                "mIoU_mean": miou_mean,
                "mIoU_std": miou_std,
                "mAcc@0.25_mean": macc_mean,
                "mAcc@0.25_std": macc_std,
            }
        )
    with (output / "lerf_ovs_standard_by_scene.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(aggregate[0].keys()))
        writer.writeheader()
        writer.writerows(aggregate)

    lookup = {(row["scene"], row["method"]): row for row in aggregate}
    lines = [
        "# Standard LERF-OVS evaluation",
        "",
        "Metrics follow pairwise frame-query aggregation. Values are percentages; +/- is sample standard deviation across seeds.",
        "",
        "| Method | "
        + " | ".join(f"{scene} mIoU / mAcc@0.25" for scene in args.scenes)
        + f" | {len(args.scenes)}-scene mean mIoU / mAcc@0.25 |",
        "|---|" + "---:|" * (len(args.scenes) + 1),
    ]
    complete_methods = []
    for method in args.methods:
        cells = []
        scene_rows = []
        for scene in args.scenes:
            row = lookup.get((scene, method))
            if row is None:
                cells.append("-")
            else:
                scene_rows.append(row)
                cells.append(
                    f"{row['mIoU_mean']:.2f} +/- {row['mIoU_std']:.2f} / "
                    f"{row['mAcc@0.25_mean']:.2f} +/- {row['mAcc@0.25_std']:.2f}"
                )
        if len(scene_rows) == len(args.scenes):
            complete_methods.append(method)
            overall = (
                f"{statistics.fmean(row['mIoU_mean'] for row in scene_rows):.2f} / "
                f"{statistics.fmean(row['mAcc@0.25_mean'] for row in scene_rows):.2f}"
            )
        else:
            overall = "INCOMPLETE"
        lines.append(f"| {method} | {' | '.join(cells)} | {overall} |")

    metadata = {
        "protocol": "LERF-OVS pairwise frame-query evaluation",
        "required_scenes": args.scenes,
        "complete_methods": complete_methods,
        "eligible_for_published_baseline_merge": len(complete_methods) > 0,
    }
    (output / "lerf_ovs_standard_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "lerf_ovs_standard_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(output / "lerf_ovs_standard_summary.md")


if __name__ == "__main__":
    main()
