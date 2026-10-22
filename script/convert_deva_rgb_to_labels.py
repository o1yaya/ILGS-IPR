#!/usr/bin/env python3
"""Convert DEVA RGB annotations into stable single-channel ILGS identity labels."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RESAMPLING = getattr(Image, "Resampling", Image)


def sorted_images(folder):
    return sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.stem,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True, help="DEVA RGB annotation directory")
    parser.add_argument("--dst", required=True, help="Output single-channel label directory")
    parser.add_argument(
        "--image_dir",
        default=None,
        help="Original image directory. Used to restore image stems when DEVA renames frames.",
    )
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    source_paths = sorted_images(Path(args.src))
    if not source_paths:
        raise FileNotFoundError(f"No DEVA annotations found in {args.src}")

    output_stems = [path.stem for path in source_paths]
    output_sizes = [None] * len(source_paths)
    mapping_mode = "matching stems"
    if args.image_dir:
        image_paths = sorted_images(Path(args.image_dir))
        image_stems = [path.stem for path in image_paths]
        source_stems = set(output_stems)
        if source_stems != set(image_stems):
            if len(source_paths) != len(image_paths):
                raise ValueError(
                    f"DEVA masks ({len(source_paths)}) and images ({len(image_paths)}) differ in count"
                )
            output_stems = image_stems
            mapping_mode = "sorted frame order"
            matched_images = image_paths
        else:
            images_by_stem = {path.stem: path for path in image_paths}
            matched_images = [images_by_stem[stem] for stem in output_stems]
        output_sizes = [Image.open(path).size for path in matched_images]

    packed_colors = set()
    for path in source_paths:
        array = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint32)
        packed = (array[..., 0] << 16) | (array[..., 1] << 8) | array[..., 2]
        packed_colors.update(int(value) for value in np.unique(packed) if value != 0)
    ordered_packed = sorted(packed_colors)
    if len(ordered_packed) > 255:
        raise ValueError(
            f"Found {len(ordered_packed)} non-background colors; uint8 ILGS labels support at most 255"
        )
    packed_to_id = {color: index + 1 for index, color in enumerate(ordered_packed)}
    lookup = np.zeros(1 << 24, dtype=np.uint8)
    for color, identity in packed_to_id.items():
        lookup[color] = identity

    destination = Path(args.dst)
    destination.mkdir(parents=True, exist_ok=True)
    file_mapping = []
    resized_frames = 0
    for source, output_stem, output_size in zip(source_paths, output_stems, output_sizes):
        array = np.asarray(Image.open(source).convert("RGB"), dtype=np.uint32)
        packed = (array[..., 0] << 16) | (array[..., 1] << 8) | array[..., 2]
        label = lookup[packed]
        if output_size and label.shape[::-1] != output_size:
            label = np.asarray(
                Image.fromarray(label, mode="L").resize(output_size, RESAMPLING.NEAREST),
                dtype=np.uint8,
            )
            resized_frames += 1
        output = destination / f"{output_stem}.png"
        Image.fromarray(label, mode="L").save(output)
        file_mapping.append({"source": source.name, "output": output.name})

    report_path = Path(args.report) if args.report else destination / "deva_label_mapping.json"
    report = {
        "mapping_mode": mapping_mode,
        "num_frames": len(source_paths),
        "num_foreground_ids": len(packed_to_id),
        "resized_to_original_resolution": resized_frames,
        "background_rgb": [0, 0, 0],
        "color_to_id": {
            f"{color >> 16},{(color >> 8) & 255},{color & 255}": identity
            for color, identity in packed_to_id.items()
        },
        "files": file_mapping,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Converted {len(source_paths)} frames with {len(packed_to_id)} foreground IDs "
        f"using {mapping_mode}."
    )
    print(f"Resized {resized_frames} label frames to the original image resolution.")
    print(f"Labels: {destination}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
