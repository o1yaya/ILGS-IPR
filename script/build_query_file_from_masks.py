#!/usr/bin/env python3
"""Extract a deterministic query list from LERF-Mask or LERF-OVS labels."""

import argparse
import json
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def queries_from_json_labels(root):
    queries = set()
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for obj in data.get("objects", []):
            category = str(obj.get("category", "")).strip()
            if category:
                queries.add(category)
    return queries


def queries_from_mask_files(root):
    queries = set()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        # A flat frame image next to a JSON annotation is not a query mask.
        if path.with_suffix(".json").is_file():
            continue
        if path.parent == root:
            continue
        queries.add(path.stem)
    return queries


def main():
    parser = argparse.ArgumentParser(
        description="Build one-query-per-line text file from segmentation annotations."
    )
    parser.add_argument("--gt_path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--frame_output",
        default=None,
        help="Optional output file containing annotated frame stems, one per line.",
    )
    args = parser.parse_args()

    root = Path(args.gt_path)
    if not root.is_dir():
        raise SystemExit(f"Ground-truth directory not found: {root}")

    queries = queries_from_json_labels(root) | queries_from_mask_files(root)
    if not queries:
        raise SystemExit(f"No query labels found under {root}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sorted(queries, key=str.casefold)) + "\n", encoding="utf-8")
    print(f"Wrote {len(queries)} queries to {output}")
    if args.frame_output:
        json_frames = {path.stem for path in root.glob("*.json")}
        frames = json_frames or {path.name for path in root.iterdir() if path.is_dir()}
        if not frames:
            raise SystemExit(f"No annotated frames found under {root}")
        frame_output = Path(args.frame_output)
        frame_output.parent.mkdir(parents=True, exist_ok=True)
        frame_output.write_text("\n".join(sorted(frames)) + "\n", encoding="utf-8")
        print(f"Wrote {len(frames)} annotated frames to {frame_output}")


if __name__ == "__main__":
    main()
