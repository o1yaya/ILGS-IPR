import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def read_label(path):
    return np.array(Image.open(path))


def save_label(path, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(label.astype(np.uint8)).save(path)


def save_confidence(path, confidence):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(confidence * 255.0, 0, 255).astype(np.uint8)).save(path)


def mode_or_none(values):
    values = values.astype(np.int64)
    if values.size == 0:
        return None
    labels, counts = np.unique(values, return_counts=True)
    return int(labels[np.argmax(counts)])


def relabel_small_components(label, min_area, ring_radius):
    refined = label.copy()
    confidence = np.ones(label.shape, dtype=np.float32)
    component_rows = []

    for object_id in np.unique(label):
        mask = label == object_id
        components, count = ndimage.label(mask)
        if count == 0:
            continue

        for component_id in range(1, count + 1):
            component = components == component_id
            area = int(component.sum())
            if area >= min_area:
                continue

            dilated = ndimage.binary_dilation(component, iterations=ring_radius)
            ring = dilated & ~component
            neighbor_values = refined[ring & (refined != object_id)]
            replacement = mode_or_none(neighbor_values)

            confidence[component] *= 0.25
            action = "low_confidence"
            if replacement is not None:
                refined[component] = replacement
                confidence[component] *= 0.5
                action = f"relabel_to_{replacement}"

            component_rows.append(
                {
                    "object_id": int(object_id),
                    "area": area,
                    "replacement": replacement,
                    "action": action,
                }
            )

    return refined, confidence, component_rows


def boundary_confidence(label, width, weight):
    if width <= 0:
        return np.ones(label.shape, dtype=np.float32)

    local_max = ndimage.maximum_filter(label, size=3)
    local_min = ndimage.minimum_filter(label, size=3)
    boundary = local_max != local_min
    if width > 1:
        boundary = ndimage.binary_dilation(boundary, iterations=width - 1)

    confidence = np.ones(label.shape, dtype=np.float32)
    confidence[boundary] *= weight
    return confidence


def collect_area_stats(mask_paths):
    areas_by_id = {}
    per_image = {}

    for path in mask_paths:
        label = read_label(path)
        image_stats = {}
        for object_id, count in zip(*np.unique(label, return_counts=True)):
            object_id = int(object_id)
            count = int(count)
            image_stats[object_id] = count
            areas_by_id.setdefault(object_id, []).append(count)
        per_image[path.name] = image_stats

    medians = {object_id: float(np.median(counts)) for object_id, counts in areas_by_id.items()}
    return medians, per_image


def apply_area_consistency(confidence, label, medians, low_factor, high_factor, weight):
    inconsistent_ids = []
    for object_id in np.unique(label):
        object_id = int(object_id)
        area = int((label == object_id).sum())
        median = medians.get(object_id, 0.0)
        if median <= 0:
            continue
        if area < median * low_factor or area > median * high_factor:
            confidence[label == object_id] *= weight
            inconsistent_ids.append(
                {
                    "object_id": object_id,
                    "area": area,
                    "median_area": median,
                }
            )
    return inconsistent_ids


def refine_dataset(args):
    dataset_path = Path(args.dataset_path)
    src_dir = dataset_path / args.src
    dst_dir = dataset_path / args.dst
    conf_dir = dataset_path / args.conf_dst
    report_dir = dataset_path / args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    mask_paths = sorted(src_dir.glob("*.png"))
    if not mask_paths:
        raise FileNotFoundError(f"No PNG object masks found under {src_dir}")

    medians, _ = collect_area_stats(mask_paths)
    summary_rows = []
    detailed = {}

    for path in mask_paths:
        label = read_label(path)
        refined, confidence, small_components = relabel_small_components(
            label, args.min_component_area, args.relabel_ring_radius
        )

        confidence *= boundary_confidence(refined, args.boundary_width, args.boundary_weight)
        inconsistent_ids = apply_area_consistency(
            confidence,
            refined,
            medians,
            args.area_low_factor,
            args.area_high_factor,
            args.area_weight,
        )

        confidence = np.clip(confidence, args.min_confidence, 1.0)

        save_label(dst_dir / path.name, refined)
        save_confidence(conf_dir / path.name, confidence)

        changed = refined != label
        low_conf = confidence < 0.999
        summary_rows.append(
            {
                "image": path.name,
                "pixels": int(label.size),
                "changed_pixels": int(changed.sum()),
                "changed_ratio": float(changed.mean()),
                "low_confidence_pixels": int(low_conf.sum()),
                "low_confidence_ratio": float(low_conf.mean()),
                "small_components": len(small_components),
                "area_inconsistent_ids": len(inconsistent_ids),
            }
        )
        detailed[path.name] = {
            "small_components": small_components,
            "area_inconsistent_ids": inconsistent_ids,
        }

    with open(report_dir / "object_mask_refine_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    with open(report_dir / "object_mask_refine_details.json", "w", encoding="utf-8") as f:
        json.dump(detailed, f, indent=2)

    print(f"source masks:      {src_dir}")
    print(f"refined masks:     {dst_dir}")
    print(f"confidence maps:   {conf_dir}")
    print(f"summary report:    {report_dir / 'object_mask_refine_summary.csv'}")
    print(f"detailed report:   {report_dir / 'object_mask_refine_details.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Refine ILGS object identity pseudo-labels before training. "
            "The script keeps the original label space, relabels tiny isolated components to "
            "their dominant neighbor, and writes per-pixel confidence maps for optional "
            "confidence-weighted object supervision."
        )
    )
    parser.add_argument("--dataset_path", required=True, help="Path such as dataset/lerf/teatime")
    parser.add_argument("--src", default="object_mask", help="Source object-mask directory")
    parser.add_argument("--dst", default="object_mask_refined", help="Output refined mask directory")
    parser.add_argument(
        "--conf_dst",
        default="object_confidence_refined",
        help="Output confidence-map directory, saved as uint8 PNG",
    )
    parser.add_argument("--report_dir", default="object_mask_refine_report")
    parser.add_argument("--min_component_area", type=int, default=64)
    parser.add_argument("--relabel_ring_radius", type=int, default=3)
    parser.add_argument("--boundary_width", type=int, default=2)
    parser.add_argument("--boundary_weight", type=float, default=0.65)
    parser.add_argument("--area_low_factor", type=float, default=0.15)
    parser.add_argument("--area_high_factor", type=float, default=6.0)
    parser.add_argument("--area_weight", type=float, default=0.50)
    parser.add_argument("--min_confidence", type=float, default=0.05)
    refine_dataset(parser.parse_args())
