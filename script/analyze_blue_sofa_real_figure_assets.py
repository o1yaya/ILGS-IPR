#!/usr/bin/env python3
"""Audit real blue_sofa masks exported for the manuscript teaser."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def load_mask(path: Path, size=None):
    with Image.open(path) as image:
        image = image.convert("L")
        if size is not None and image.size != size:
            image = image.resize(size, Image.Resampling.NEAREST)
        return np.asarray(image) >= 128, image.size


def metrics(gt, pred):
    intersection = np.logical_and(gt, pred).sum()
    union = np.logical_or(gt, pred).sum()
    gt_area = max(1, int(gt.sum()))
    pred_area = max(1, int(pred.sum()))
    fp = np.logical_and(~gt, pred).sum()
    fn = np.logical_and(gt, ~pred).sum()
    return {
        "iou": float(intersection / union) if union else 1.0,
        "precision": float(intersection / pred_area),
        "recall": float(intersection / gt_area),
        "fp_gt": float(fp / gt_area),
        "fn_gt": float(fn / gt_area),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for record in manifest["records"]:
        view_dir = args.root / f'view_{record["test_index"]}_{record["image_stem"]}'
        query_dir = view_dir / record["query"]
        gt, size = load_mask(query_dir / "ground_truth.png")
        official, _ = load_mask(query_dir / "official_ilgs.png", size)
        ipr, _ = load_mask(query_dir / "ipr.png", size)
        official_metrics = metrics(gt, official)
        ipr_metrics = metrics(gt, ipr)
        row = {
            "view": record["test_index"],
            "stem": record["image_stem"],
            "query": record["query"],
            "official": official_metrics,
            "ipr": ipr_metrics,
            "delta_iou": ipr_metrics["iou"] - official_metrics["iou"],
            "delta_fp_gt": ipr_metrics["fp_gt"] - official_metrics["fp_gt"],
            "delta_fn_gt": ipr_metrics["fn_gt"] - official_metrics["fn_gt"],
        }
        rows.append(row)

    print("view\tquery\toff_iou\tipr_iou\tdelta\toff_fp\tipr_fp\toff_fn\tipr_fn")
    for row in sorted(rows, key=lambda item: (item["query"], -item["delta_iou"])):
        off = row["official"]
        ipr = row["ipr"]
        print(
            f'{row["view"]}\t{row["query"]}\t'
            f'{off["iou"]:.3f}\t{ipr["iou"]:.3f}\t{row["delta_iou"]:+.3f}\t'
            f'{off["fp_gt"]:.3f}\t{ipr["fp_gt"]:.3f}\t'
            f'{off["fn_gt"]:.3f}\t{ipr["fn_gt"]:.3f}'
        )

    print("\nBest positive real view per query:")
    for query in manifest["queries"]:
        candidates = [row for row in rows if row["query"] == query]
        best = max(candidates, key=lambda item: item["delta_iou"])
        print(
            f'{query}: view {best["view"]} (frame {best["stem"]}), '
            f'IoU {best["official"]["iou"]:.3f} -> {best["ipr"]["iou"]:.3f} '
            f'({best["delta_iou"]:+.3f})'
        )


if __name__ == "__main__":
    main()
