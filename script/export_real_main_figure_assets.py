#!/usr/bin/env python3
"""Export real, protocol-aligned assets for the manuscript method figures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_DATASET_ROOT = Path("/media/cx/data/cxdata/3DOVS")
DEFAULT_OFFICIAL_ROOT = Path("/media/cx/data/cxdata/ilgs_3dovs/output/3dovs")
DEFAULT_IPR_ROOT = Path(
    "/media/cx/data/cxdata/ilgs_3dovs_consistency_t075_pilot/output/3dovs"
)
RAW_MASK_DIR = "object_mask"
CLEAN_MASK_DIR = "object_mask_refined_trainonly_strict"
CONFIDENCE_DIR = "object_confidence_ipr_trainview_consistency_strict"
REPORT_DIR = "object_mask_ipr_trainview_consistency_strict_report"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Package real 3D-OVS inputs and model outputs for an editable method "
            "figure. No masks are synthesized or manually altered."
        )
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--official-root", type=Path, default=DEFAULT_OFFICIAL_ROOT)
    parser.add_argument("--ipr-root", type=Path, default=DEFAULT_IPR_ROOT)
    parser.add_argument(
        "--scenes", nargs="+", default=["bench", "covered_desk"]
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "/media/cx/data/cxdata/datasets/real_main_figure_assets_20261018"
        ),
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, target: Path, records: list[dict]) -> bool:
    if not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    records.append(
        {
            "source": str(source.resolve()),
            "relative_output": str(target),
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        }
    )
    return True


def copy_tree(source: Path, target: Path, records: list[dict]) -> bool:
    if not source.is_dir():
        return False
    for path in sorted(source.rglob("*")):
        if path.is_file():
            copy_file(path, target / path.relative_to(source), records)
    return True


def image_for_stem(directory: Path, stem: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png", ".JPG", ".PNG"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def load_label(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(path)
    if size is not None and image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image)


def rank_training_frames(scene_dir: Path) -> list[dict]:
    raw_dir = scene_dir / RAW_MASK_DIR
    clean_dir = scene_dir / CLEAN_MASK_DIR
    confidence_dir = scene_dir / CONFIDENCE_DIR
    rows = []
    for raw_path in sorted(raw_dir.glob("*.png")):
        clean_path = clean_dir / raw_path.name
        confidence_path = confidence_dir / raw_path.name
        if not clean_path.is_file() or not confidence_path.is_file():
            continue
        raw_image = Image.open(raw_path)
        raw = np.asarray(raw_image)
        clean = load_label(clean_path, raw_image.size)
        confidence = np.asarray(
            Image.open(confidence_path)
            .convert("L")
            .resize(raw_image.size, Image.Resampling.NEAREST),
            dtype=np.float32,
        )
        changed_ratio = float(np.mean(raw != clean))
        mean_reliability = float(np.mean(confidence) / 255.0)
        low_reliability_ratio = float(np.mean(confidence < 254.5))
        score = changed_ratio + 0.5 * low_reliability_ratio + 0.25 * (
            1.0 - mean_reliability
        )
        rows.append(
            {
                "stem": raw_path.stem,
                "score": score,
                "changed_pixel_ratio": changed_ratio,
                "low_reliability_pixel_ratio": low_reliability_ratio,
                "mean_reliability": mean_reliability,
            }
        )
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def read_frame_names(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(index): Path(str(name)).stem
        for index, name in data.items()
    }


def copy_render_frame(
    base: Path,
    output: Path,
    index: str,
    records: list[dict],
) -> None:
    key = f"{int(index):05d}"
    candidates = {
        "render_rgb.png": base / "renders" / f"{key}.png",
        "identity_feature.png": base / "objects_feature16" / f"{key}.png",
        "language_feature.npy": base / "feature_map_npy" / f"{key}.npy",
        "identity_logits.npy": base / "logits" / f"{key}_logits.npy",
    }
    for name, source in candidates.items():
        copy_file(source, output / name, records)


def export_model(
    model_dir: Path,
    output: Path,
    selected_stems: set[str],
    records: list[dict],
) -> dict:
    status = {"model": str(model_dir), "exists": model_dir.is_dir(), "phases": {}}
    if not model_dir.is_dir():
        return status

    copy_file(model_dir / "cfg_args", output / "cfg_args", records)
    for phase in ("train", "test"):
        base = model_dir / phase / "ours_30000_text"
        frame_names_path = base / "frame_names.json"
        frame_names = read_frame_names(frame_names_path)
        phase_status = {
            "base": str(base),
            "frame_manifest_found": bool(frame_names),
            "copied_frames": [],
        }
        copy_file(frame_names_path, output / phase / "frame_names.json", records)

        if phase == "train":
            chosen = [
                (index, stem)
                for index, stem in frame_names.items()
                if stem in selected_stems
            ]
        else:
            chosen = list(frame_names.items())

        for index, stem in chosen:
            frame_output = output / phase / "frames" / stem
            copy_render_frame(base, frame_output, index, records)
            phase_status["copied_frames"].append(
                {"index": f"{int(index):05d}", "stem": stem}
            )

        if phase == "test":
            copy_tree(base / "test_mask", output / phase / "test_mask", records)
        status["phases"][phase] = phase_status
    return status


def find_dataset_root(args: argparse.Namespace) -> Path:
    if args.dataset_root.is_dir():
        return args.dataset_root
    fallback = args.repo / "dataset" / "3dovs"
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError(
        f"3D-OVS dataset root not found: {args.dataset_root} or {fallback}"
    )


def main() -> None:
    args = parse_args()
    dataset_root = find_dataset_root(args)
    output = args.output.resolve()
    archive = output.with_suffix(".tar.gz")
    if output.exists():
        if not args.force:
            raise FileExistsError(f"Output already exists: {output}; use --force")
        shutil.rmtree(output)
    if archive.exists():
        if not args.force:
            raise FileExistsError(f"Archive already exists: {archive}; use --force")
        archive.unlink()
    output.mkdir(parents=True)

    records: list[dict] = []
    manifest = {
        "purpose": "Real assets for the ILGS-IPR pipeline and method figures",
        "protocol": "strict_trainview_consistency",
        "seed": 0,
        "manual_mask_editing": False,
        "dataset_root": str(dataset_root.resolve()),
        "official_root": str(args.official_root.resolve()),
        "ipr_root": str(args.ipr_root.resolve()),
        "scenes": {},
    }

    for scene in args.scenes:
        scene_dir = dataset_root / scene
        if not scene_dir.is_dir():
            raise FileNotFoundError(f"Missing scene: {scene_dir}")
        ranking = rank_training_frames(scene_dir)
        if not ranking:
            raise RuntimeError(
                f"No aligned raw/clean/confidence frames found for {scene}"
            )
        selected = ranking[: args.top_k]
        selected_stems = {row["stem"] for row in selected}
        scene_output = output / scene

        copy_tree(scene_dir / "images", scene_output / "dataset" / "images", records)
        copy_tree(
            scene_dir / "images_train",
            scene_output / "dataset" / "images_train",
            records,
        )
        copy_tree(
            scene_dir / "test_mask",
            scene_output / "dataset" / "test_mask",
            records,
        )
        copy_tree(
            scene_dir / REPORT_DIR,
            scene_output / "dataset" / REPORT_DIR,
            records,
        )

        for row in selected:
            stem = row["stem"]
            frame_output = scene_output / "training_frames" / stem
            image_path = image_for_stem(scene_dir / "images", stem)
            if image_path is None:
                image_path = image_for_stem(scene_dir / "images_train", stem)
            if image_path is not None:
                copy_file(
                    image_path,
                    frame_output / f"rgb{image_path.suffix.lower()}",
                    records,
                )
            copy_file(
                scene_dir / RAW_MASK_DIR / f"{stem}.png",
                frame_output / "noisy_identity_labels.png",
                records,
            )
            copy_file(
                scene_dir / CLEAN_MASK_DIR / f"{stem}.png",
                frame_output / "cleaned_identity_labels.png",
                records,
            )
            copy_file(
                scene_dir / CONFIDENCE_DIR / f"{stem}.png",
                frame_output / "reliability_map.png",
                records,
            )
            for feature_name in (f"{stem}_f.npy", f"{stem}.npy"):
                feature_path = scene_dir / "language_features_dim3" / feature_name
                if copy_file(
                    feature_path,
                    frame_output / "language_feature_gt.npy",
                    records,
                ):
                    break

        official_model = args.official_root / f"{scene}_ipr_official_s0"
        ipr_model = args.ipr_root / (
            f"{scene}_ipr_strict_trainview_consistency_s0"
        )
        scene_manifest = {
            "selected_training_frames": selected,
            "selection_rule": (
                "Highest combined raw-vs-clean label change and low-reliability "
                "pixel score; selection is automatic and recorded."
            ),
            "models": {
                "official": export_model(
                    official_model,
                    scene_output / "models" / "official",
                    selected_stems,
                    records,
                ),
                "ipr": export_model(
                    ipr_model,
                    scene_output / "models" / "ipr",
                    selected_stems,
                    records,
                ),
            },
        }
        manifest["scenes"][scene] = scene_manifest

    manifest["files"] = records
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with tarfile.open(archive, "w:gz") as handle:
        handle.add(output, arcname=output.name)

    print(json.dumps({
        "output": str(output),
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive),
        "scenes": args.scenes,
        "selected_frames": {
            scene: [
                row["stem"] for row in manifest["scenes"][scene]["selected_training_frames"]
            ]
            for scene in args.scenes
        },
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
