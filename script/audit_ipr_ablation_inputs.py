import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


VARIANTS = {
    "base_confidence": (
        "object_confidence_refined_trainonly_strict",
        None,
    ),
    "consistency_only": (
        "object_confidence_ipr_trainview_consistency_only_strict",
        "object_mask_ipr_trainview_consistency_only_strict_report/object_semantics.json",
    ),
    "large_only": (
        "object_confidence_ipr_trainview_large_only_strict",
        "object_mask_ipr_trainview_large_only_strict_report/object_semantics.json",
    ),
    "full": (
        "object_confidence_ipr_trainview_consistency_strict",
        "object_mask_ipr_trainview_consistency_strict_report/object_semantics.json",
    ),
}


def load_maps(folder):
    paths = sorted(folder.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"No confidence maps found in {folder}")
    return {path.name: np.asarray(Image.open(path).convert("L"), dtype=np.uint8) for path in paths}


def main():
    parser = argparse.ArgumentParser(description="Audit strict IPR ablation inputs.")
    parser.add_argument("--dataset_root", default="dataset/lerf")
    parser.add_argument("--scenes", nargs="+", default=["ramen", "figurines", "teatime"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for scene in args.scenes:
        root = Path(args.dataset_root) / scene
        loaded = {}
        for variant, (folder_name, report_name) in VARIANTS.items():
            maps = load_maps(root / folder_name)
            loaded[variant] = maps
            means = [float(arr.mean()) / 255.0 for arr in maps.values()]
            reasons = Counter()
            if report_name:
                report = json.loads((root / report_name).read_text(encoding="utf-8"))
                reasons.update(x["reason"] for x in report["object_weights"].values())
            rows.append(
                {
                    "scene": scene,
                    "variant": variant,
                    "frames": len(maps),
                    "mean_confidence": float(np.mean(means)),
                    "reasons": dict(sorted(reasons.items())),
                }
            )

        names = set(loaded["base_confidence"])
        for variant, maps in loaded.items():
            if set(maps) != names:
                raise RuntimeError(f"{scene}/{variant}: confidence-map filenames differ from the base set")
            for name in names:
                if maps[name].shape != loaded["base_confidence"][name].shape:
                    raise RuntimeError(f"{scene}/{variant}/{name}: confidence-map shape mismatch")

        for variant in ("consistency_only", "large_only", "full"):
            changed = sum(
                int(np.count_nonzero(loaded[variant][name] != loaded["base_confidence"][name]))
                for name in names
            )
            total = sum(loaded[variant][name].size for name in names)
            next(row for row in rows if row["scene"] == scene and row["variant"] == variant)[
                "changed_pixel_ratio_vs_base"
            ] = changed / total

    output.write_text(json.dumps({"scenes": rows}, indent=2), encoding="utf-8")
    print(json.dumps({"scenes": rows}, indent=2))


if __name__ == "__main__":
    main()
