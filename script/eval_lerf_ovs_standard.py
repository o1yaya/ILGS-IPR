#!/usr/bin/env python3
"""Evaluate masks with the standard LERF-OVS pairwise mIoU/mAcc protocol."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def normalize_name(value):
    return " ".join(str(value).strip().casefold().split())


def load_binary(path, threshold):
    image = Image.open(path).convert("L")
    return np.asarray(image) > threshold


def polygon_mask(shape, polygons):
    height, width = shape
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    if not polygons:
        return np.asarray(image) > 0
    if isinstance(polygons[0], (int, float)):
        polygon_list = [polygons]
    elif (
        isinstance(polygons[0], (list, tuple))
        and len(polygons[0]) == 2
        and all(isinstance(value, (int, float)) for value in polygons[0])
    ):
        polygon_list = [polygons]
    else:
        polygon_list = polygons
    for polygon in polygon_list:
        if not polygon:
            continue
        if isinstance(polygon[0], (list, tuple)):
            points = [(float(x), float(y)) for x, y in polygon]
        else:
            points = list(zip(polygon[0::2], polygon[1::2]))
        if len(points) >= 3:
            draw.polygon(points, fill=255)
    return np.asarray(image) > 0


def load_annotations(root, gt_threshold):
    """Return (frame, query, mask, source) tuples for supported layouts."""
    records = []
    json_paths = sorted(root.glob("*.json"))
    if json_paths:
        for path in json_paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            info = data.get("info", {})
            height = int(info.get("height", 0))
            width = int(info.get("width", 0))
            if height <= 0 or width <= 0:
                frame_image = next(
                    (path.with_suffix(ext) for ext in IMAGE_SUFFIXES if path.with_suffix(ext).is_file()),
                    None,
                )
                if frame_image is None:
                    raise ValueError(f"Missing image dimensions for {path}")
                width, height = Image.open(frame_image).size
            by_query = defaultdict(list)
            for obj in data.get("objects", []):
                query = str(obj.get("category", "")).strip()
                if query:
                    by_query[query].append(obj.get("segmentation", []))
            for query, segmentations in sorted(by_query.items()):
                merged = np.zeros((height, width), dtype=bool)
                for segmentation in segmentations:
                    merged |= polygon_mask((height, width), segmentation)
                records.append((path.stem, query, merged, str(path)))
        return records, "polygon-json"

    for frame_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for path in sorted(frame_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                records.append((frame_dir.name, path.stem, load_binary(path, gt_threshold), str(path)))
    return records, "nested-mask"


def load_frame_map(path):
    if path is None:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {f"{idx:05d}": str(name) for idx, name in enumerate(data)}
    if not isinstance(data, dict):
        raise ValueError("Frame map must be a JSON object or list.")
    return {str(key): str(value) for key, value in data.items()}


def index_predictions(root, frame_map):
    reverse_map = {normalize_name(value): key for key, value in frame_map.items()}
    index = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if len(relative.parts) >= 2:
            raw_frame = relative.parts[-2]
            query = path.stem
        else:
            stem = path.stem
            candidates = sorted(frame_map.values(), key=len, reverse=True)
            matched = next((name for name in candidates if stem.startswith(name + "_")), None)
            if matched is not None:
                raw_frame, query = matched, stem[len(matched) + 1 :]
            elif "_" in stem:
                raw_frame, query = stem.split("_", 1)
            else:
                continue
        frame = frame_map.get(raw_frame, raw_frame)
        index[(normalize_name(frame), normalize_name(query))] = path
        # Also index by numeric folder in case the GT already uses indices.
        index.setdefault((normalize_name(raw_frame), normalize_name(query)), path)
    return index, reverse_map


def resize_bool(mask, shape):
    image = Image.fromarray(mask.astype(np.uint8) * 255)
    image = image.resize((shape[1], shape[0]), Image.Resampling.NEAREST)
    return np.asarray(image) > 0


def iou(gt, pred):
    union = np.logical_or(gt, pred).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(gt, pred).sum() / union)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "LERF-OVS evaluation: average IoU over frame-query pairs and the fraction "
            "of pairs whose IoU is greater than the selected accuracy threshold."
        )
    )
    parser.add_argument("--gt_path", required=True)
    parser.add_argument("--pred_path", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--frame_map", default=None)
    parser.add_argument("--scene", default="unknown")
    parser.add_argument("--method", default="unknown")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--acc_threshold", type=float, default=0.25)
    parser.add_argument("--gt_threshold", type=int, default=10)
    parser.add_argument("--pred_threshold", type=int, default=10)
    parser.add_argument(
        "--allow_missing",
        action="store_true",
        help="Score missing predictions as zero. The default is strict failure.",
    )
    args = parser.parse_args()

    gt_root = Path(args.gt_path)
    pred_root = Path(args.pred_path)
    if not gt_root.is_dir():
        raise SystemExit(f"Ground-truth directory not found: {gt_root}")
    if not pred_root.is_dir():
        raise SystemExit(f"Prediction directory not found: {pred_root}")

    annotations, gt_layout = load_annotations(gt_root, args.gt_threshold)
    if not annotations:
        raise SystemExit(f"No annotations found under {gt_root}")
    frame_map = load_frame_map(args.frame_map)
    predictions, reverse_map = index_predictions(pred_root, frame_map)

    rows = []
    missing = []
    for frame, query, gt, source in annotations:
        key = (normalize_name(frame), normalize_name(query))
        pred_path = predictions.get(key)
        if pred_path is None:
            numeric = reverse_map.get(normalize_name(frame))
            if numeric is not None:
                pred_path = predictions.get((normalize_name(numeric), normalize_name(query)))
        if pred_path is None:
            missing.append({"frame": frame, "query": query})
            score = 0.0
            pred_source = ""
        else:
            pred = load_binary(pred_path, args.pred_threshold)
            if pred.shape != gt.shape:
                pred = resize_bool(pred, gt.shape)
            score = iou(gt, pred)
            pred_source = str(pred_path)
        rows.append(
            {
                "frame": frame,
                "query": query,
                "iou": score,
                "success_at_threshold": int(score > args.acc_threshold),
                "gt_path": source,
                "pred_path": pred_source,
            }
        )

    if missing and not args.allow_missing:
        preview = ", ".join(f"{x['frame']}/{x['query']}" for x in missing[:8])
        raise SystemExit(
            f"Missing {len(missing)} of {len(rows)} predictions. Examples: {preview}. "
            "Use --allow_missing only when zero-scoring missing outputs is intentional."
        )

    by_query = defaultdict(list)
    for row in rows:
        by_query[row["query"]].append(row["iou"])
    query_rows = [
        {
            "query": query,
            "n_pairs": len(values),
            "mean_iou": float(np.mean(values)),
            "acc_at_threshold": float(np.mean(np.asarray(values) > args.acc_threshold)),
        }
        for query, values in sorted(by_query.items(), key=lambda item: item[0].casefold())
    ]

    scores = np.asarray([row["iou"] for row in rows], dtype=np.float64)
    summary = {
        "protocol": "LERF-OVS pairwise evaluation",
        "aggregation": "mean over all annotated frame-query pairs",
        "gt_layout": gt_layout,
        "scene": args.scene,
        "method": args.method,
        "seed": args.seed,
        "n_pairs": len(rows),
        "n_queries": len(by_query),
        "missing_predictions": len(missing),
        "miou": float(scores.mean()),
        "macc_at_threshold": float(np.mean(scores > args.acc_threshold)),
        "acc_threshold": args.acc_threshold,
        "macro_query_miou_auxiliary": float(np.mean([x["mean_iou"] for x in query_rows])),
    }

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (output / "queries.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(query_rows[0].keys()))
        writer.writeheader()
        writer.writerows(query_rows)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "missing_predictions.json").write_text(
        json.dumps(missing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Scene: {args.scene}")
    print(f"Pairs: {summary['n_pairs']} (missing: {summary['missing_predictions']})")
    print(f"Standard LERF-OVS mIoU: {summary['miou']:.6f}")
    print(f"Standard LERF-OVS mAcc@{args.acc_threshold:g}: {summary['macc_at_threshold']:.6f}")
    print(f"Report: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
