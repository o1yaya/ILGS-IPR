#!/usr/bin/env python3
"""Adapt the original 3D-OVS layout to ILGS without modifying source images."""

import argparse
import json
import os
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def image_files(folder):
    return sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.stem,
    )


def link_or_copy(source, destination, mode):
    if destination.exists() or destination.is_symlink():
        return
    if mode == "copy":
        shutil.copy2(source, destination)
    elif mode == "hardlink":
        os.link(source, destination)
    else:
        try:
            destination.symlink_to(os.path.relpath(source, destination.parent))
        except OSError:
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)


def prepare_scene(scene_dir, mode):
    images_dir = scene_dir / "images"
    segmentations_dir = scene_dir / "segmentations"
    classes_path = segmentations_dir / "classes.txt"
    if not images_dir.is_dir() or not segmentations_dir.is_dir() or not classes_path.is_file():
        raise FileNotFoundError(
            f"{scene_dir} must contain images/ and segmentations/classes.txt"
        )

    images = image_files(images_dir)
    images_by_stem = {path.stem: path for path in images}
    test_stems = sorted(
        path.name for path in segmentations_dir.iterdir() if path.is_dir()
    )
    missing_images = [stem for stem in test_stems if stem not in images_by_stem]
    if missing_images:
        raise FileNotFoundError(
            f"Segmentation views without matching images in {scene_dir.name}: {missing_images}"
        )

    classes = [
        line.strip()
        for line in classes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not classes:
        raise ValueError(f"No classes listed in {classes_path}")

    train_dir = scene_dir / "images_train"
    train_dir.mkdir(exist_ok=True)
    test_stem_set = set(test_stems)
    for source in images:
        if source.stem not in test_stem_set:
            link_or_copy(source.resolve(), train_dir / source.name, mode)

    queries_path = scene_dir / "queries.txt"
    queries_path.write_text("\n".join(classes) + "\n", encoding="utf-8")

    test_mask_dir = scene_dir / "test_mask"
    test_mask_dir.mkdir(exist_ok=True)
    mapping = []
    for index, stem in enumerate(test_stems):
        source_dir = segmentations_dir / stem
        destination_dir = test_mask_dir / str(index)
        destination_dir.mkdir(exist_ok=True)
        missing_classes = []
        for query in classes:
            source = source_dir / f"{query}.png"
            if not source.is_file():
                missing_classes.append(query)
                continue
            shutil.copy2(source, destination_dir / source.name)
        if missing_classes:
            raise FileNotFoundError(
                f"Missing masks for view {stem} in {scene_dir.name}: {missing_classes}"
            )
        mapping.append({"test_index": index, "image_stem": stem})

    metadata = {
        "scene": scene_dir.name,
        "num_images": len(images),
        "num_train_images": len(images) - len(test_stems),
        "num_test_images": len(test_stems),
        "queries": classes,
        "test_view_mapping": mapping,
    }
    (scene_dir / "ilgs_3dovs_layout.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(
        f"[{scene_dir.name}] train={metadata['num_train_images']} "
        f"test={metadata['num_test_images']} classes={len(classes)}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset_root", default="dataset/3dovs")
    parser.add_argument("--scenes", nargs="*", default=None)
    parser.add_argument(
        "--train_image_mode",
        choices=["symlink", "hardlink", "copy"],
        default="symlink",
    )
    args = parser.parse_args()

    root = Path(args.dataset_root)
    scenes = args.scenes or sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "segmentations" / "classes.txt").is_file()
    )
    if not scenes:
        raise ValueError(f"No 3D-OVS scenes found under {root}")
    for scene in scenes:
        prepare_scene(root / scene, args.train_image_mode)


if __name__ == "__main__":
    main()
