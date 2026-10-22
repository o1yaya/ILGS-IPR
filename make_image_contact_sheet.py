#!/usr/bin/env python3
"""Create a labelled contact sheet from an image directory."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image_dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=10)
    parser.add_argument("--tile_width", type=int, default=192)
    parser.add_argument("--tile_height", type=int, default=120)
    parser.add_argument("--label_height", type=int, default=18)
    parser.add_argument("--limit", type=int, default=0, help="0 keeps all images")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.columns <= 0 or args.tile_width <= 0 or args.tile_height <= 0:
        raise ValueError("columns and tile dimensions must be positive")

    image_paths = sorted(
        path for path in args.image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if args.limit > 0:
        image_paths = image_paths[: args.limit]
    if not image_paths:
        raise FileNotFoundError(f"No images found in {args.image_dir}")

    rows = math.ceil(len(image_paths) / args.columns)
    tile_total_height = args.tile_height + args.label_height
    sheet = Image.new(
        "RGB",
        (args.columns * args.tile_width, rows * tile_total_height),
        (12, 12, 12),
    )

    for index, path in enumerate(image_paths):
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((args.tile_width, args.tile_height), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (args.tile_width, tile_total_height), (12, 12, 12))
        x_offset = (args.tile_width - image.width) // 2
        y_offset = (args.tile_height - image.height) // 2
        tile.paste(image, (x_offset, y_offset))
        ImageDraw.Draw(tile).text(
            (4, args.tile_height + 2), path.stem, fill=(245, 245, 245)
        )
        x = (index % args.columns) * args.tile_width
        y = (index // args.columns) * tile_total_height
        sheet.paste(tile, (x, y))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_options = {"quality": 92} if args.output.suffix.lower() in {".jpg", ".jpeg"} else {}
    sheet.save(args.output, **save_options)
    print(f"images: {len(image_paths)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
