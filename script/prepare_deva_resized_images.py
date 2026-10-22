#!/usr/bin/env python3
"""Create low-resolution image copies for memory-safe DEVA/SAM inference."""

import argparse
import shutil
from pathlib import Path

from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
RESAMPLING = getattr(Image, "Resampling", Image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--min_side", type=int, default=480)
    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help="Exact downsampling factor. Overrides --min_side when provided.",
    )
    args = parser.parse_args()

    source_dir = Path(args.src)
    destination_dir = Path(args.dst)
    destination_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(
        path for path in source_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not paths:
        raise FileNotFoundError(f"No images found in {source_dir}")

    resized = copied = 0
    for source in paths:
        destination = destination_dir / source.name
        with Image.open(source) as image:
            width, height = image.size
            current_min = min(width, height)
            if args.scale is not None:
                if args.scale <= 0:
                    raise ValueError("--scale must be positive")
                size = (max(1, round(width / args.scale)), max(1, round(height / args.scale)))
            elif current_min <= args.min_side:
                shutil.copy2(source, destination)
                copied += 1
                continue
            else:
                scale = args.min_side / current_min
                size = (max(1, round(width * scale)), max(1, round(height * scale)))
            output = image.convert("RGB").resize(size, RESAMPLING.LANCZOS)
            save_kwargs = {"quality": 95, "subsampling": 0} if destination.suffix.lower() in {".jpg", ".jpeg"} else {}
            output.save(destination, **save_kwargs)
            resized += 1

    print(
        f"Prepared {len(paths)} DEVA inputs in {destination_dir}: "
        f"{resized} resized, {copied} copied."
    )


if __name__ == "__main__":
    main()
