#!/usr/bin/env python3
"""Merge reproduced LERF-OVS results with provenance-marked published baselines."""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


STANDARD_SCENES = ["waldo_kitchen", "ramen", "figurines", "teatime"]


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reproduced_by_scene", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument(
        "--published",
        default="config/lerf_ovs_published_baselines.csv",
    )
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    if metadata.get("required_scenes") != STANDARD_SCENES:
        raise SystemExit(
            "Refusing to merge: reproduced report does not use the canonical four-scene order "
            f"{STANDARD_SCENES}."
        )
    complete_methods = metadata.get("complete_methods", [])
    if not complete_methods:
        raise SystemExit("Refusing to merge: no reproduced method is complete on all four scenes.")

    published = read_csv(args.published)
    reproduced_raw = read_csv(args.reproduced_by_scene)
    reproduced = []
    for row in reproduced_raw:
        if row["method"] not in complete_methods:
            continue
        reproduced.append(
            {
                "method": row["method"],
                "scene": row["scene"],
                "mIoU": row["mIoU_mean"],
                "mAcc@0.25": row["mAcc@0.25_mean"],
                "source_kind": "reproduced_in_this_work",
                "source": "current experiment logs",
                "protocol_note": "Four-scene LERF-OVS pairwise evaluation",
            }
        )

    combined = published + reproduced
    by_method = defaultdict(dict)
    provenance = {}
    for row in combined:
        by_method[row["method"]][row["scene"]] = row
        provenance[row["method"]] = row["source_kind"]

    for method, scene_rows in by_method.items():
        missing = [scene for scene in STANDARD_SCENES if scene not in scene_rows]
        if missing:
            raise SystemExit(f"Method {method} is missing scenes: {missing}")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "lerf_ovs_baselines_long.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(combined[0].keys()))
        writer.writeheader()
        writer.writerows(combined)

    published_order = ["LangSplat", "OpenGaussian", "Dr.Splat", "CAGS"]
    methods = published_order + [m for m in complete_methods if m not in published_order]
    lines = [
        "# LERF-OVS comparison with provenance",
        "",
        "Published rows are transcribed from CAGS and are not claimed as independent reproductions. All values are percentages.",
        "",
        "| Method | Provenance | "
        + " | ".join(f"{scene} mIoU / mAcc@0.25" for scene in STANDARD_SCENES)
        + " | Mean mIoU / mAcc@0.25 |",
        "|---|---|" + "---:|" * (len(STANDARD_SCENES) + 1),
    ]
    for method in methods:
        if method not in by_method:
            continue
        scene_rows = [by_method[method][scene] for scene in STANDARD_SCENES]
        cells = [f"{float(row['mIoU']):.2f} / {float(row['mAcc@0.25']):.2f}" for row in scene_rows]
        mean_miou = statistics.fmean(float(row["mIoU"]) for row in scene_rows)
        mean_macc = statistics.fmean(float(row["mAcc@0.25"]) for row in scene_rows)
        label = "published (CAGS table)" if provenance[method] == "reported_by_CAGS" else "reproduced"
        lines.append(
            f"| {method} | {label} | {' | '.join(cells)} | {mean_miou:.2f} / {mean_macc:.2f} |"
        )

    report = output / "lerf_ovs_comparison.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
