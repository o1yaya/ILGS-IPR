import argparse
import csv
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_points_ply(path, points, colors):
    points = np.asarray(points, dtype=np.float32)
    colors = np.asarray(colors)
    if colors.dtype != np.uint8:
        colors = np.clip(colors * 255.0 if colors.max() <= 1.0 else colors, 0, 255).astype(np.uint8)

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from plyfile import PlyData, PlyElement

        rows = np.empty(
            len(points),
            dtype=[
                ("x", "f4"),
                ("y", "f4"),
                ("z", "f4"),
                ("red", "u1"),
                ("green", "u1"),
                ("blue", "u1"),
            ],
        )
        rows["x"], rows["y"], rows["z"] = points[:, 0], points[:, 1], points[:, 2]
        rows["red"], rows["green"], rows["blue"] = colors[:, 0], colors[:, 1], colors[:, 2]
        PlyData([PlyElement.describe(rows, "vertex")]).write(str(path))
        return
    except ModuleNotFoundError:
        pass

    with path.open("w", encoding="ascii") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for point, color in zip(points, colors):
            f.write(
                f"{point[0]:.8f} {point[1]:.8f} {point[2]:.8f} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )


def load_request(path):
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path / "anygrasp_sdk_request.npz"
    if not path.exists():
        raise FileNotFoundError(f"AnyGrasp request not found: {path}")
    return path, np.load(path, allow_pickle=True)


def create_anygrasp_detector(args):
    if args.sdk_path:
        sys.path.insert(0, str(Path(args.sdk_path).expanduser().resolve()))
    try:
        gsnet = importlib.import_module("gsnet")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Could not import AnyGrasp SDK module 'gsnet'. Pass --sdk_path to the AnyGrasp SDK "
            "directory, or run this script inside the SDK environment."
        ) from exc

    if not hasattr(gsnet, "create_detector"):
        raise AttributeError("Imported gsnet, but it has no create_detector(config) function.")

    config = SimpleNamespace(
        checkpoint_path=args.checkpoint_path,
        max_gripper_width=args.max_gripper_width,
        gripper_height=args.gripper_height,
        top_down_grasp=args.top_down_grasp,
        debug=args.debug,
    )
    return gsnet.create_detector(config)


def extract_grasp_array(grasp_group):
    for name in ("grasp_group_array", "grasp_array", "array"):
        if hasattr(grasp_group, name):
            value = getattr(grasp_group, name)
            value = value() if callable(value) else value
            array = np.asarray(value)
            if array.ndim == 2 and len(array) > 0:
                return array.astype(np.float32)
    try:
        array = np.asarray(grasp_group)
        if array.ndim == 2 and len(array) > 0:
            return array.astype(np.float32)
    except Exception:
        pass
    return None


def grasp_to_record(grasp, index, target_center):
    score = float(getattr(grasp, "score", np.nan))
    width = float(getattr(grasp, "width", np.nan))
    height = float(getattr(grasp, "height", np.nan))
    depth = float(getattr(grasp, "depth", np.nan))
    translation = np.asarray(getattr(grasp, "translation", [np.nan, np.nan, np.nan]), dtype=np.float32)
    rotation = np.asarray(getattr(grasp, "rotation_matrix", np.eye(3)), dtype=np.float32)
    world_translation = translation + target_center
    return {
        "index": int(index),
        "score": score,
        "width": width,
        "height": height,
        "depth": depth,
        "translation_centered": translation.astype(float).tolist(),
        "translation_world": world_translation.astype(float).tolist(),
        "rotation_matrix": rotation.astype(float).tolist(),
    }


def iter_grasps(grasp_group):
    try:
        return list(grasp_group)
    except TypeError:
        return []


def approach_axis_from_array(row):
    if len(row) >= 17:
        rot = row[4:13].reshape(3, 3)
        return rot[:, 0], row[13:16]
    return None, None


def normal_guided_scores(grasp_array, target_points, target_normals):
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(target_points)
        translations = grasp_array[:, 13:16]
        _, nearest = tree.query(translations, k=1, workers=-1)
        normals = target_normals[nearest]
    except Exception:
        translations = grasp_array[:, 13:16]
        nearest = []
        for point in translations:
            dist = np.sum((target_points - point[None, :]) ** 2, axis=1)
            nearest.append(int(np.argmin(dist)))
        normals = target_normals[np.asarray(nearest)]

    rotations = grasp_array[:, 4:13].reshape(-1, 3, 3)
    approach = rotations[:, :, 0]
    approach_norm = np.linalg.norm(approach, axis=1, keepdims=True)
    normal_norm = np.linalg.norm(normals, axis=1, keepdims=True)
    approach = approach / np.maximum(approach_norm, 1e-8)
    normals = normals / np.maximum(normal_norm, 1e-8)
    return np.abs(np.sum(approach * normals, axis=1)).astype(np.float32)


def save_candidates_from_array(out_dir, grasp_array, target_center, target_points, target_normals, args):
    if grasp_array is None or len(grasp_array) == 0:
        return [], None

    scores = grasp_array[:, 0].astype(np.float32) if grasp_array.shape[1] > 0 else np.zeros(len(grasp_array), dtype=np.float32)
    ranking_score = scores.copy()
    normal_score = None
    if args.normal_guided and grasp_array.shape[1] >= 16:
        normal_score = normal_guided_scores(grasp_array, target_points, target_normals)
        ranking_score = scores + float(args.normal_weight) * normal_score

    order = np.argsort(-ranking_score)
    if args.top_k > 0:
        order = order[: args.top_k]
    selected = grasp_array[order]
    np.save(out_dir / "grasp_candidates_raw.npy", grasp_array.astype(np.float32))
    np.save(out_dir / "grasp_candidates_selected.npy", selected.astype(np.float32))

    if selected.shape[1] >= 16:
        centers = selected[:, 13:16]
        if args.coordinate_mode == "centered":
            centers_world = centers + target_center[None, :]
        else:
            centers_world = centers
        color_score = ranking_score[order]
        norm_score = (color_score - color_score.min()) / max(float(color_score.max() - color_score.min()), 1e-8)
        colors = np.stack(
            [
                255 * norm_score,
                180 * (1.0 - norm_score) + 60 * norm_score,
                255 * (1.0 - norm_score),
            ],
            axis=1,
        ).astype(np.uint8)
        write_points_ply(out_dir / "grasp_candidate_centers_centered.ply", centers, colors)
        write_points_ply(out_dir / "grasp_candidate_centers_world.ply", centers_world, colors)

    rows = []
    for rank, idx in enumerate(order):
        row = grasp_array[idx]
        record = {
            "rank": int(rank),
            "source_index": int(idx),
            "score": float(scores[idx]),
            "ranking_score": float(ranking_score[idx]),
        }
        if normal_score is not None:
            record["normal_alignment"] = float(normal_score[idx])
        if row.shape[0] >= 16:
            center = row[13:16].astype(np.float32)
            record["translation_centered"] = center.astype(float).tolist()
            record["translation_world"] = (center + target_center).astype(float).tolist()
            record["rotation_matrix"] = row[4:13].reshape(3, 3).astype(float).tolist()
            record["width"] = float(row[1])
            record["height"] = float(row[2])
            record["depth"] = float(row[3])
        rows.append(record)

    write_json(out_dir / "grasp_candidates.json", rows)
    with (out_dir / "grasp_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["rank", "source_index", "score", "ranking_score", "normal_alignment", "width", "height", "depth", "tx", "ty", "tz"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            translation = row.get("translation_centered", [np.nan, np.nan, np.nan])
            writer.writerow(
                {
                    "rank": row.get("rank"),
                    "source_index": row.get("source_index"),
                    "score": row.get("score"),
                    "ranking_score": row.get("ranking_score"),
                    "normal_alignment": row.get("normal_alignment", ""),
                    "width": row.get("width", ""),
                    "height": row.get("height", ""),
                    "depth": row.get("depth", ""),
                    "tx": translation[0],
                    "ty": translation[1],
                    "tz": translation[2],
                }
            )
    return rows, selected


def run_inference(args):
    request_path, request = load_request(args.request)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else request_path.parent / "grasp_candidates"
    out_dir.mkdir(parents=True, exist_ok=True)

    points = request["points"].astype(np.float32)
    target_points = request["target_points"].astype(np.float32)
    target_normals = request["target_normals"].astype(np.float32)
    target_center = request["target_center"].astype(np.float32)
    coordinate_mode = str(request["coordinate_mode"]) if "coordinate_mode" in request else args.coordinate_mode
    if coordinate_mode not in {"centered", "world"}:
        coordinate_mode = args.coordinate_mode
    args.coordinate_mode = coordinate_mode

    params = {
        "dense_grasp": bool(args.dense_grasp),
        "collision_detection": not bool(args.no_collision_detection),
    }
    if args.use_region_steering and "region_mask" in request:
        params["region_steering"] = request["region_mask"].astype(bool)
    if "approach_steering" in request and len(request["approach_steering"]) == 3:
        params["approach_steering"] = request["approach_steering"].astype(np.float32)
        params["approach_thresh"] = float(args.approach_thresh)

    detector = create_anygrasp_detector(args)
    result = detector.get_grasp(points, params)
    grasp_group = result[0] if isinstance(result, tuple) else result
    if grasp_group is None:
        report = {
            "request": str(request_path),
            "output_dir": str(out_dir),
            "candidate_count_raw": 0,
            "candidate_count_saved": 0,
            "message": "AnyGrasp returned no grasp output.",
        }
        write_json(out_dir / "anygrasp_inference_report.json", report)
        return report

    if not args.dense_grasp and hasattr(grasp_group, "nms"):
        grasp_group = grasp_group.nms()
    if hasattr(grasp_group, "sort_by_score"):
        grasp_group = grasp_group.sort_by_score()

    grasp_array = extract_grasp_array(grasp_group)
    object_grasps = iter_grasps(grasp_group)
    rows, selected = save_candidates_from_array(out_dir, grasp_array, target_center, target_points, target_normals, args)

    if not rows and object_grasps:
        rows = [grasp_to_record(grasp, i, target_center) for i, grasp in enumerate(object_grasps[: args.top_k])]
        write_json(out_dir / "grasp_candidates.json", rows)

    report = {
        "request": str(request_path),
        "output_dir": str(out_dir),
        "sdk_path": args.sdk_path,
        "checkpoint_path": args.checkpoint_path,
        "coordinate_mode": coordinate_mode,
        "points": int(len(points)),
        "target_points": int(len(target_points)),
        "params": {
            key: (value.tolist() if hasattr(value, "tolist") else value)
            for key, value in params.items()
            if key != "region_steering"
        },
        "workspace_lims_reference": [
            float(request["workspace_min"][0]),
            float(request["workspace_max"][0]),
            float(request["workspace_min"][1]),
            float(request["workspace_max"][1]),
            float(request["workspace_min"][2]),
            float(request["workspace_max"][2]),
        ],
        "use_region_steering": bool(args.use_region_steering and "region_mask" in request),
        "candidate_count_raw": 0 if grasp_array is None else int(len(grasp_array)),
        "candidate_count_saved": int(len(rows)),
        "files": {
            "raw_npy": str(out_dir / "grasp_candidates_raw.npy"),
            "selected_npy": str(out_dir / "grasp_candidates_selected.npy"),
            "json": str(out_dir / "grasp_candidates.json"),
            "csv": str(out_dir / "grasp_candidates.csv"),
            "centers_centered_ply": str(out_dir / "grasp_candidate_centers_centered.ply"),
            "centers_world_ply": str(out_dir / "grasp_candidate_centers_world.ply"),
        },
    }
    write_json(out_dir / "anygrasp_inference_report.json", report)
    return report


def parse_args():
    parser = argparse.ArgumentParser(description="Run AnyGrasp SDK inference on an ILGS-prepared request package.")
    parser.add_argument("--request", required=True, help="Path to anygrasp_sdk_request.npz or its directory")
    parser.add_argument("--checkpoint_path", required=True)
    parser.add_argument("--sdk_path", default="", help="Path to AnyGrasp SDK directory containing gsnet.py")
    parser.add_argument("--output_dir", default="")
    parser.add_argument("--coordinate_mode", choices=["centered", "world"], default="centered")
    parser.add_argument("--max_gripper_width", type=float, default=0.08)
    parser.add_argument("--gripper_height", type=float, default=0.03)
    parser.add_argument("--top_down_grasp", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--dense_grasp", action="store_true")
    parser.add_argument("--no_collision_detection", action="store_true")
    parser.add_argument("--use_region_steering", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--approach_thresh", type=float, default=float(np.pi), help="Approach steering threshold in radians")
    parser.add_argument("--normal_guided", action="store_true")
    parser.add_argument("--normal_weight", type=float, default=0.2)
    parser.add_argument("--top_k", type=int, default=50)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(run_inference(parse_args()), indent=2))
