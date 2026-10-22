#!/usr/bin/env python3
"""Audit whether existing checkpoints can be evaluated on LERF-OVS labels."""

import argparse
import json
from pathlib import Path


STANDARD_SCENES = ["waldo_kitchen", "ramen", "figurines", "teatime"]


def annotation_frames(path):
    json_frames = {p.stem for p in path.glob("*.json")}
    if json_frames:
        return json_frames
    return {p.name for p in path.iterdir() if p.is_dir()}


def image_stems(scene_path):
    images = scene_path / "images"
    if not images.is_dir():
        return set()
    return {p.stem for p in images.iterdir() if p.is_file()}


def train_image_stems(scene_path):
    images = scene_path / "images_train"
    if not images.is_dir():
        return set()
    return {p.stem for p in images.iterdir() if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_root", required=True)
    parser.add_argument("--label_root", required=True)
    parser.add_argument("--model_root", required=True)
    parser.add_argument("--methods", nargs="+", default=["official", "ipr"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--scenes", nargs="+", default=STANDARD_SCENES)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    label_root = Path(args.label_root)
    model_root = Path(args.model_root)
    scene_rows = []
    reusable = True

    for scene in args.scenes:
        scene_path = dataset_root / scene
        gt_path = label_root / scene
        if (gt_path / "gt").is_dir():
            gt_path = gt_path / "gt"
        frames = annotation_frames(gt_path) if gt_path.is_dir() else set()
        images = image_stems(scene_path)
        train_images = train_image_stems(scene_path)
        missing_frames = sorted(frames - images)
        frames_in_train = sorted(frames & train_images)
        frames_in_heldout = sorted(frames - train_images)
        models = {}
        for method in args.methods:
            for seed in args.seeds:
                name = f"{scene}_ipr_{method}_s{seed}"
                ckpt = model_root / name / "point_cloud" / "iteration_30000"
                complete = (ckpt / "point_cloud.ply").is_file() and (ckpt / "classifier.pth").is_file()
                models[f"{method}_s{seed}"] = complete
        scene_ok = scene_path.is_dir() and gt_path.is_dir() and bool(frames) and not missing_frames and all(models.values())
        reusable &= scene_ok
        scene_rows.append(
            {
                "scene": scene,
                "dataset_exists": scene_path.is_dir(),
                "labels_exist": gt_path.is_dir(),
                "annotation_frames": len(frames),
                "dataset_images": len(images),
                "training_images": len(train_images),
                "missing_annotation_frames": missing_frames,
                "annotation_frames_in_train_split": frames_in_train,
                "annotation_frames_in_heldout_split": frames_in_heldout,
                "models": models,
                "reusable": scene_ok,
            }
        )

    report = {
        "standard_scenes": STANDARD_SCENES,
        "requested_scenes": args.scenes,
        "all_reusable": reusable,
        "scenes": scene_rows,
        "note": (
            "LERF-Mask checkpoints are reusable only when their source images contain every official "
            "LERF-OVS annotated frame. Evaluation must render both train and held-out camera splits, "
            "because official annotations can occur in either split."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if reusable else 2)


if __name__ == "__main__":
    main()
