#!/usr/bin/env python3
"""Render ILGS object predictions using source image names.

Unlike render.py, this utility exports train and test views into one directory
and preserves each camera's image_name. The named masks can therefore be
paired exactly with registered RGB-D frames.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from arguments import ModelParams, PipelineParams, get_combined_args
from gaussian_renderer import GaussianModel, render
from scene import Scene
from utils.general_utils import safe_state


def render_named_masks(dataset, pipeline, iteration, target_class, threshold, output_dir):
    dataset.eval = True
    gaussians = GaussianModel(dataset.sh_degree)
    scene = Scene(dataset, gaussians, load_iteration=iteration, shuffle=False)

    if not 0 <= target_class < dataset.num_classes:
        raise ValueError(
            f"target_class={target_class} is outside [0, {dataset.num_classes - 1}]"
        )

    classifier = torch.nn.Conv2d(gaussians.num_objects, dataset.num_classes, kernel_size=1)
    classifier = classifier.cuda().eval()
    classifier_path = (
        Path(dataset.model_path)
        / "point_cloud"
        / f"iteration_{scene.loaded_iter}"
        / "classifier.pth"
    )
    classifier.load_state_dict(torch.load(classifier_path, map_location="cuda"))

    output_dir = Path(output_dir) if output_dir else (
        Path(dataset.model_path) / "rgbd_object_export" / f"iteration_{scene.loaded_iter}"
    )
    masks_dir = output_dir / "masks"
    probabilities_dir = output_dir / "probabilities"
    masks_dir.mkdir(parents=True, exist_ok=True)
    probabilities_dir.mkdir(parents=True, exist_ok=True)

    background_color = [1, 1, 1] if dataset.white_background else [0, 0, 0]
    background = torch.tensor(background_color, dtype=torch.float32, device="cuda")
    records = []

    split_views = (
        ("train", scene.getTrainCameras()),
        ("test", scene.getTestCameras()),
    )
    with torch.no_grad():
        for split, views in split_views:
            print(f"Rendering {len(views)} {split} views")
            for index, view in enumerate(views, start=1):
                rendered = render(view, gaussians, pipeline, background)
                logits = classifier(rendered["render_object"])
                probability = torch.softmax(logits, dim=0)[target_class]
                mask = probability >= threshold

                image_name = f"{view.image_name}.png"
                np.save(
                    probabilities_dir / f"{view.image_name}.npy",
                    probability.cpu().numpy().astype(np.float16),
                )
                Image.fromarray(mask.cpu().numpy().astype(np.uint8) * 255).save(
                    masks_dir / image_name
                )
                records.append(
                    {
                        "image": image_name,
                        "split": split,
                        "target_pixels": int(mask.sum().item()),
                        "mean_target_probability": float(probability[mask].mean().item())
                        if mask.any()
                        else 0.0,
                    }
                )
                print(
                    f"[{split} {index:02d}/{len(views):02d}] {image_name}: "
                    f"{records[-1]['target_pixels']} target pixels"
                )

    report = {
        "model_path": str(Path(dataset.model_path).resolve()),
        "iteration": int(scene.loaded_iter),
        "num_classes": int(dataset.num_classes),
        "target_class": int(target_class),
        "probability_threshold": float(threshold),
        "train_views": len(scene.getTrainCameras()),
        "test_views": len(scene.getTestCameras()),
        "output_dir": str(output_dir.resolve()),
        "frames": records,
    }
    (output_dir / "render_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render named binary ILGS masks for an RGB-D sequence."
    )
    model = ModelParams(parser, sentinel=True)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", type=int, default=-1)
    parser.add_argument("--target_class", type=int, default=1)
    parser.add_argument("--probability_threshold", type=float, default=0.5)
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--quiet", action="store_true")
    args = get_combined_args(parser)
    safe_state(args.quiet)
    render_named_masks(
        model.extract(args),
        pipeline.extract(args),
        args.iteration,
        args.target_class,
        args.probability_threshold,
        args.output_dir,
    )
