import argparse
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path


NAME_RE = re.compile(r"^eval_(.+?)_ipr_(.+)_s(\d+)\.txt$")
MIOU_RE = re.compile(r"^Overall Mean IoU:\s*([0-9.eE+-]+)\s*$", re.MULTILINE)
MBIOU_RE = re.compile(r"^Overall Boundary Mean IoU:\s*([0-9.eE+-]+)\s*$", re.MULTILINE)
VARIANT_ORDER = [
    "official",
    "cleanup",
    "cleanup_conf",
    "no_semantic",
    "no_visibility",
    "semantic_only",
    "large_only",
    "no_large",
    "full",
]


def mean_std(values):
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def main():
    parser = argparse.ArgumentParser(description="Summarize controlled IPR ablation logs.")
    parser.add_argument("--log_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument(
        "--scenes",
        nargs="*",
        default=["figurines", "ramen", "teatime"],
        help="Scene order used in the Markdown table.",
    )
    parser.add_argument(
        "--variants",
        nargs="*",
        default=VARIANT_ORDER,
        help="Variant order used in the Markdown table.",
    )
    parser.add_argument("--title", default="Controlled IPR ablation")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_rows = []
    for path in sorted(log_dir.glob("eval_*_ipr_*_s*.txt")):
        match = NAME_RE.match(path.name)
        if not match:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        miou_match = MIOU_RE.search(text)
        mbiou_match = MBIOU_RE.search(text)
        if not miou_match or not mbiou_match:
            continue
        scene, variant, seed = match.groups()
        if scene not in args.scenes or variant not in args.variants:
            continue
        raw_rows.append(
            {
                "scene": scene,
                "variant": variant,
                "seed": int(seed),
                "mIoU": float(miou_match.group(1)) * 100.0,
                "mBIoU": float(mbiou_match.group(1)) * 100.0,
            }
        )

    if not raw_rows:
        raise SystemExit(f"No complete evaluation logs found in {log_dir}")

    with (output_dir / "controlled_ablation_raw.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scene", "variant", "seed", "mIoU", "mBIoU"])
        writer.writeheader()
        writer.writerows(raw_rows)

    grouped = defaultdict(list)
    for row in raw_rows:
        grouped[(row["scene"], row["variant"])].append(row)

    aggregate_rows = []
    for (scene, variant), rows in sorted(grouped.items()):
        miou_mean, miou_std = mean_std([r["mIoU"] for r in rows])
        mbiou_mean, mbiou_std = mean_std([r["mBIoU"] for r in rows])
        aggregate_rows.append(
            {
                "scene": scene,
                "variant": variant,
                "n": len(rows),
                "mIoU_mean": miou_mean,
                "mIoU_std": miou_std,
                "mBIoU_mean": mbiou_mean,
                "mBIoU_std": mbiou_std,
            }
        )

    with (output_dir / "controlled_ablation_by_scene.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(aggregate_rows[0].keys()))
        writer.writeheader()
        writer.writerows(aggregate_rows)

    scene_means = defaultdict(list)
    for row in aggregate_rows:
        scene_means[row["variant"]].append(row)

    lines = [
        f"# {args.title}",
        "",
        "All values are percentages. Each scene value is mean +/- sample standard deviation across seeds.",
        "",
        "| Variant | "
        + " | ".join(f"{scene} mIoU / mBIoU" for scene in args.scenes)
        + f" | {len(args.scenes)}-scene mean mIoU / mBIoU |",
        "|---|" + "---:|" * (len(args.scenes) + 1),
    ]
    lookup = {(r["scene"], r["variant"]): r for r in aggregate_rows}
    for variant in args.variants:
        cells = []
        available = []
        for scene in args.scenes:
            row = lookup.get((scene, variant))
            if row is None:
                cells.append("-")
            else:
                available.append(row)
                cells.append(
                    f'{row["mIoU_mean"]:.2f} +/- {row["mIoU_std"]:.2f} / '
                    f'{row["mBIoU_mean"]:.2f} +/- {row["mBIoU_std"]:.2f}'
                )
        if available:
            overall_miou = statistics.fmean(r["mIoU_mean"] for r in available)
            overall_mbiou = statistics.fmean(r["mBIoU_mean"] for r in available)
            overall = f"{overall_miou:.2f} / {overall_mbiou:.2f}"
        else:
            overall = "-"
        lines.append(f"| {variant} | {' | '.join(cells)} | {overall} |")

    report_path = output_dir / "controlled_ablation_summary.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    main()
