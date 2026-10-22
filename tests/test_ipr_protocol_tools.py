import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[1]


def run_script(name, *args, expected=0):
    result = subprocess.run(
        [sys.executable, str(REPO / "script" / name), *map(str, args)],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"{name} returned {result.returncode}, expected {expected}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def save_mask(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(values, dtype=np.uint8)).save(path)


class LerfOvsEvaluationTests(unittest.TestCase):
    def test_nested_masks_and_frame_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt = root / "gt" / "frame_00053"
            pred = root / "pred" / "00000"
            mask = np.zeros((32, 32), dtype=np.uint8)
            mask[:16, :16] = 255
            save_mask(gt / "red cup.jpg", mask)
            # Match the benchmark's thresholded JPEG ground truth exactly.
            thresholded_gt = (np.asarray(Image.open(gt / "red cup.jpg").convert("L")) > 10) * 255
            save_mask(pred / "red cup.png", thresholded_gt)
            frame_map = root / "frame_names.json"
            frame_map.write_text(json.dumps({"00000": "frame_00053"}), encoding="utf-8")
            output = root / "report"

            run_script(
                "build_query_file_from_masks.py",
                "--gt_path", gt.parent,
                "--output", root / "queries.txt",
                "--frame_output", root / "frames.txt",
            )
            self.assertEqual((root / "queries.txt").read_text().strip(), "red cup")
            self.assertEqual((root / "frames.txt").read_text().strip(), "frame_00053")

            run_script(
                "eval_lerf_ovs_standard.py",
                "--gt_path", gt.parent,
                "--pred_path", pred.parent,
                "--frame_map", frame_map,
                "--output_dir", output,
                "--scene", "figurines",
                "--method", "ipr",
            )
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(summary["miou"], 1.0)
            self.assertAlmostEqual(summary["macc_at_threshold"], 1.0)
            self.assertEqual(summary["n_pairs"], 1)

    def test_polygon_json_merges_same_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gt = root / "gt"
            gt.mkdir()
            annotation = {
                "info": {"height": 4, "width": 4},
                "objects": [
                    {"category": "cup", "segmentation": [[0, 0], [1, 0], [1, 1], [0, 1]]},
                    {"category": "cup", "segmentation": [[2, 2], [3, 2], [3, 3], [2, 3]]},
                ],
            }
            (gt / "frame_00001.json").write_text(json.dumps(annotation), encoding="utf-8")
            pred_mask = np.zeros((4, 4), dtype=np.uint8)
            pred_mask[:2, :2] = 255
            pred_mask[2:, 2:] = 255
            save_mask(root / "pred" / "frame_00001" / "cup.png", pred_mask)

            run_script(
                "eval_lerf_ovs_standard.py",
                "--gt_path", gt,
                "--pred_path", root / "pred",
                "--output_dir", root / "report",
            )
            summary = json.loads((root / "report" / "summary.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(summary["miou"], 1.0)
            self.assertEqual(summary["gt_layout"], "polygon-json")

    def test_missing_prediction_fails_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_mask(root / "gt" / "frame" / "cup.png", [[255]])
            (root / "pred").mkdir()
            run_script(
                "eval_lerf_ovs_standard.py",
                "--gt_path", root / "gt",
                "--pred_path", root / "pred",
                "--output_dir", root / "report",
                expected=1,
            )


class StrictProtocolTests(unittest.TestCase):
    def test_train_view_subset_excludes_nontraining_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp)
            for stem in ("train_a", "test_b"):
                save_mask(dataset / "object_mask_refined" / f"{stem}.png", [[1]])
                save_mask(dataset / "object_confidence_refined" / f"{stem}.png", [[255]])
            save_mask(dataset / "images_train" / "train_a.png", [[255]])

            run_script("subset_ipr_training_views.py", "--dataset_path", dataset)
            self.assertTrue((dataset / "object_mask_refined_trainonly" / "train_a.png").is_file())
            self.assertFalse((dataset / "object_mask_refined_trainonly" / "test_b.png").exists())
            manifest = json.loads(
                (dataset / "object_mask_refined_trainonly" / "subset_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["n_train_views"], 1)

    def test_train_view_mask_only_subset_needs_no_confidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp)
            save_mask(dataset / "object_mask" / "train_a.png", [[1]])
            save_mask(dataset / "object_mask" / "test_b.png", [[2]])
            save_mask(dataset / "images_train" / "train_a.png", [[255]])

            run_script(
                "subset_ipr_training_views.py",
                "--dataset_path", dataset,
                "--mask_src", "object_mask",
                "--mask_dst", "object_mask_trainonly_raw",
                "--mask_only",
            )
            output = dataset / "object_mask_trainonly_raw"
            self.assertTrue((output / "train_a.png").is_file())
            self.assertFalse((output / "test_b.png").exists())
            manifest = json.loads(
                (output / "subset_manifest.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(manifest["confidence_source"])
            self.assertNotIn("confidence", manifest["operations"][0])

    def test_baseline_merge_requires_and_accepts_four_scenes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reproduced = root / "by_scene.csv"
            with reproduced.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "scene", "method", "n_seeds", "mIoU_mean", "mIoU_std",
                        "mAcc@0.25_mean", "mAcc@0.25_std",
                    ],
                )
                writer.writeheader()
                for scene in ("waldo_kitchen", "ramen", "figurines", "teatime"):
                    writer.writerow(
                        {
                            "scene": scene,
                            "method": "ipr",
                            "n_seeds": 1,
                            "mIoU_mean": 50,
                            "mIoU_std": 0,
                            "mAcc@0.25_mean": 70,
                            "mAcc@0.25_std": 0,
                        }
                    )
            metadata = root / "metadata.json"
            metadata.write_text(
                json.dumps(
                    {
                        "required_scenes": ["waldo_kitchen", "ramen", "figurines", "teatime"],
                        "complete_methods": ["ipr"],
                    }
                ),
                encoding="utf-8",
            )
            run_script(
                "merge_lerf_ovs_baselines.py",
                "--reproduced_by_scene", reproduced,
                "--metadata", metadata,
                "--published", REPO / "config" / "lerf_ovs_published_baselines.csv",
                "--output_dir", root / "out",
            )
            text = (root / "out" / "lerf_ovs_comparison.md").read_text(encoding="utf-8")
            self.assertIn("CAGS", text)
            self.assertIn("reproduced", text)


if __name__ == "__main__":
    unittest.main()
