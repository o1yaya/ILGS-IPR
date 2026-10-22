#!/usr/bin/env python3
"""Summarize the paired seed-0 released-ILGS protocol check."""

import argparse
import json
import math
import re
from pathlib import Path


PUBLISHED = {
    "ramen": (84.3, 75.5),
    "figurines": (75.9, 73.8),
    "teatime": (81.2, 78.8),
}

DISPLAY = {
    "official": "ILGS released code (seed 0)",
    "ipr": "ILGS released code + IPR (seed 0)",
}


def parse_metrics(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    miou_match = re.search(r"Overall Mean IoU:\s*([0-9.eE+-]+)", text)
    mbiou_match = re.search(r"Overall Boundary Mean IoU:\s*([0-9.eE+-]+)", text)
    if not miou_match or not mbiou_match:
        raise ValueError(f"Could not parse released ILGS metrics from {path}")
    values = (100.0 * float(miou_match.group(1)), 100.0 * float(mbiou_match.group(1)))
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"Non-finite metric in {path}: {values}")
    return values


def format_pair(values):
    return f"{values[0]:.2f} / {values[1]:.2f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scenes", nargs="+", required=True)
    parser.add_argument("--variants", nargs="+", required=True)
    args = parser.parse_args()

    results = {}
    for variant in args.variants:
        results[variant] = {}
        for scene in args.scenes:
            log = args.root / "logs" / "eval" / f"{scene}_{variant}_s0.txt"
            results[variant][scene] = parse_metrics(log)

    headers = ["Method"] + [f"{scene} mIoU / mBIoU" for scene in args.scenes] + [
        f"{len(args.scenes)}-scene mean mIoU / mBIoU"
    ]
    rows = []

    if all(scene in PUBLISHED for scene in args.scenes):
        published_values = [PUBLISHED[scene] for scene in args.scenes]
        published_mean = tuple(
            sum(value[index] for value in published_values) / len(published_values)
            for index in range(2)
        )
        rows.append(
            ["ILGS paper (reported reference)"]
            + [format_pair(value) for value in published_values]
            + [format_pair(published_mean)]
        )

    for variant in args.variants:
        values = [results[variant][scene] for scene in args.scenes]
        mean = tuple(sum(value[index] for value in values) / len(values) for index in range(2))
        rows.append(
            [DISPLAY.get(variant, variant)]
            + [format_pair(value) for value in values]
            + [format_pair(mean)]
        )
        results[variant]["mean"] = mean

    report_dir = args.root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = report_dir / "official_paper_protocol_seed0.md"
    json_path = report_dir / "official_paper_protocol_seed0.json"

    lines = [
        "# Released ILGS protocol: seed-0 paired check",
        "",
        (
            "Values are percentages. The paper row is an unpaired reported reference; "
            "only the two released-code rows form a controlled comparison."
        ),
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)

    if "official" in results and "ipr" in results:
        delta = tuple(
            results["ipr"]["mean"][index] - results["official"]["mean"][index]
            for index in range(2)
        )
        lines.extend(
            [
                "",
                f"Paired IPR gain: {delta[0]:+.2f} mIoU / {delta[1]:+.2f} mBIoU points.",
            ]
        )

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "seed": 0,
                "scenes": args.scenes,
                "variants": args.variants,
                "metrics_percent": results,
                "published_reference_percent": {
                    scene: PUBLISHED[scene] for scene in args.scenes if scene in PUBLISHED
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(markdown_path)


if __name__ == "__main__":
    main()
