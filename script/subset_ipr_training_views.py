#!/usr/bin/env python3
"""Create an auditable train-view-only mask/confidence subset without deleting data."""

import argparse
import json
import os
import shutil
from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def files_by_stem(root):
    result = {}
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            if path.stem in result:
                raise ValueError(f"Duplicate stem {path.stem!r} in {root}")
            result[path.stem] = path
    return result


def materialize(source, destination, mode):
    if destination.exists():
        if destination.stat().st_size == source.stat().st_size:
            return "existing"
        raise FileExistsError(f"Refusing to overwrite a different file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "copy":
        shutil.copy2(source, destination)
        return "copy"
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy-fallback"


def require_clean_destination(root, expected_names):
    if not root.exists():
        return
    extras = sorted(
        path.name
        for path in root.iterdir()
        if path.is_file() and path.name not in expected_names and path.name != "subset_manifest.json"
    )
    if extras:
        raise SystemExit(
            f"Destination {root} contains stale files not in the train split: {extras[:8]}. "
            "Move the directory aside before rebuilding it."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_path", required=True)
    parser.add_argument("--image_train_dir", default="images_train")
    parser.add_argument("--mask_src", default="object_mask_refined")
    parser.add_argument("--confidence_src", default="object_confidence_refined")
    parser.add_argument("--mask_dst", default="object_mask_refined_trainonly")
    parser.add_argument("--confidence_dst", default="object_confidence_refined_trainonly")
    parser.add_argument(
        "--mask_only",
        action="store_true",
        help="Materialize only masks; do not require or copy confidence maps.",
    )
    parser.add_argument("--mode", choices=["hardlink", "copy"], default="hardlink")
    args = parser.parse_args()

    dataset = Path(args.dataset_path)
    train_dir = dataset / args.image_train_dir
    mask_src = dataset / args.mask_src
    conf_src = dataset / args.confidence_src
    mask_dst = dataset / args.mask_dst
    conf_dst = dataset / args.confidence_dst
    required = [train_dir, mask_src]
    if not args.mask_only:
        required.append(conf_src)
    for path in required:
        if not path.is_dir():
            raise SystemExit(f"Required directory not found: {path}")

    train_stems = sorted(files_by_stem(train_dir))
    masks = files_by_stem(mask_src)
    confidences = {} if args.mask_only else files_by_stem(conf_src)
    missing_masks = [stem for stem in train_stems if stem not in masks]
    missing_conf = [] if args.mask_only else [stem for stem in train_stems if stem not in confidences]
    if missing_masks or missing_conf:
        raise SystemExit(
            f"Train-view subset is incomplete. Missing masks={missing_masks[:8]}, "
            f"missing confidence={missing_conf[:8]}"
        )

    expected_mask_names = {masks[stem].name for stem in train_stems}
    expected_conf_names = (
        set() if args.mask_only else {confidences[stem].name for stem in train_stems}
    )
    require_clean_destination(mask_dst, expected_mask_names)
    if not args.mask_only:
        require_clean_destination(conf_dst, expected_conf_names)

    operations = []
    for stem in train_stems:
        mask_op = materialize(masks[stem], mask_dst / masks[stem].name, args.mode)
        entry = {
            "stem": stem,
            "mask": masks[stem].name,
            "mask_operation": mask_op,
        }
        if not args.mask_only:
            conf_op = materialize(confidences[stem], conf_dst / confidences[stem].name, args.mode)
            entry.update(
                {
                    "confidence": confidences[stem].name,
                    "confidence_operation": conf_op,
                }
            )
        operations.append(entry)

    manifest = {
        "dataset": str(dataset),
        "split_source": str(train_dir),
        "n_train_views": len(train_stems),
        "mask_source": str(mask_src),
        "confidence_source": None if args.mask_only else str(conf_src),
        "operations": operations,
    }
    output_roots = [mask_dst]
    if not args.mask_only:
        output_roots.append(conf_dst)
    for root in output_roots:
        root.mkdir(parents=True, exist_ok=True)
        (root / "subset_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"Prepared {len(train_stems)} train-view masks in {mask_dst}")
    if not args.mask_only:
        print(f"Prepared {len(train_stems)} train-view confidence maps in {conf_dst}")


if __name__ == "__main__":
    main()
