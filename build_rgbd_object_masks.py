#!/usr/bin/env python3
"""Associate per-frame SAM regions into RGB-D-aware object identity masks."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Segment:
    local_id: int
    area: int
    centroid: np.ndarray
    voxels: set[tuple[int, int, int]]
    descriptor: np.ndarray


@dataclass
class Track:
    track_id: int
    centroid: np.ndarray
    descriptor: np.ndarray
    voxels: set[tuple[int, int, int]] = field(default_factory=set)
    frame_indices: set[int] = field(default_factory=set)
    total_area: int = 0
    observations: int = 0


def quaternion_xyzw_to_rotation(quaternion: np.ndarray) -> np.ndarray:
    x, y, z, w = quaternion / np.linalg.norm(quaternion)
    return np.asarray(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float32,
    )


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-8 else vector


def load_segments(
    dataset: Path,
    frame: dict,
    mask_level: int,
    min_area: int,
    max_area_ratio: float,
    min_depth: float,
    max_depth: float,
    max_segment_points: int,
    voxel_size: float,
    intrinsics: dict,
    depth_factor: float,
) -> tuple[np.ndarray, list[Segment]]:
    stem = Path(frame["image"]).stem
    seg_maps = np.load(dataset / "language_features" / f"{stem}_s.npy")
    features = np.load(dataset / "language_features" / f"{stem}_f.npy").astype(np.float32)
    if mask_level < 0 or mask_level >= seg_maps.shape[0]:
        raise ValueError(f"mask_level={mask_level} is invalid for {stem}: {seg_maps.shape}")
    seg_map = seg_maps[mask_level].astype(np.int32)
    depth = np.asarray(Image.open(dataset / frame["depth"]), dtype=np.float32) / depth_factor
    if depth.shape != seg_map.shape:
        raise ValueError(f"Depth/segmentation shape mismatch for {stem}: {depth.shape} vs {seg_map.shape}")

    height, width = seg_map.shape
    max_area = int(height * width * max_area_ratio)
    fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
    cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    rotation_wc = quaternion_xyzw_to_rotation(
        np.asarray(frame["quaternion_world_from_camera_xyzw"], dtype=np.float32)
    )
    translation_wc = np.asarray(frame["translation_world_from_camera_m"], dtype=np.float32)

    segments: list[Segment] = []
    local_ids, counts = np.unique(seg_map[seg_map >= 0], return_counts=True)
    for local_id, area in zip(local_ids.tolist(), counts.tolist()):
        if area < min_area or area > max_area or local_id >= len(features):
            continue
        rows, cols = np.nonzero(seg_map == local_id)
        valid = np.isfinite(depth[rows, cols])
        valid &= depth[rows, cols] >= min_depth
        valid &= depth[rows, cols] <= max_depth
        rows, cols = rows[valid], cols[valid]
        if len(rows) < 20:
            continue
        if len(rows) > max_segment_points:
            sample_indices = np.linspace(0, len(rows) - 1, max_segment_points).astype(np.int64)
            rows, cols = rows[sample_indices], cols[sample_indices]
        z = depth[rows, cols]
        points_camera = np.stack(
            ((cols.astype(np.float32) - cx) * z / fx,
             (rows.astype(np.float32) - cy) * z / fy,
             z),
            axis=1,
        )
        points_world = points_camera @ rotation_wc.T + translation_wc
        voxel_indices = np.floor(points_world / voxel_size).astype(np.int32)
        voxels = set(map(tuple, voxel_indices.tolist()))
        if len(voxels) < 5:
            continue
        segments.append(
            Segment(
                local_id=int(local_id),
                area=int(area),
                centroid=np.median(points_world, axis=0),
                voxels=voxels,
                descriptor=normalize(features[local_id]),
            )
        )
    return seg_map, segments


def match_score(segment: Segment, track: Track, max_centroid_distance: float) -> tuple[float, dict]:
    intersection = len(segment.voxels.intersection(track.voxels))
    overlap = intersection / max(1, min(len(segment.voxels), len(track.voxels)))
    distance = float(np.linalg.norm(segment.centroid - track.centroid))
    semantic = float(np.dot(segment.descriptor, track.descriptor))
    distance_score = math.exp(-distance / max(max_centroid_distance, 1e-6))
    score = 0.55 * overlap + 0.25 * max(0.0, semantic) + 0.20 * distance_score
    return score, {"overlap": overlap, "distance": distance, "semantic": semantic}


def update_track(track: Track, segment: Segment, frame_index: int, max_track_voxels: int) -> None:
    weight = float(track.observations)
    track.centroid = (track.centroid * weight + segment.centroid) / (weight + 1.0)
    track.descriptor = normalize((track.descriptor * weight + segment.descriptor) / (weight + 1.0))
    track.voxels.update(segment.voxels)
    if len(track.voxels) > max_track_voxels:
        track.voxels = set(sorted(track.voxels)[:: max(1, len(track.voxels) // max_track_voxels)])
        if len(track.voxels) > max_track_voxels:
            track.voxels = set(sorted(track.voxels)[:max_track_voxels])
    track.frame_indices.add(frame_index)
    track.total_area += segment.area
    track.observations += 1


def associate_frame(
    segments: list[Segment],
    tracks: dict[int, Track],
    frame_index: int,
    next_track_id: int,
    args: argparse.Namespace,
) -> tuple[dict[int, tuple[int, float]], int]:
    candidate_pairs: list[tuple[float, int, int]] = []
    diagnostics: dict[tuple[int, int], dict] = {}
    for segment_index, segment in enumerate(segments):
        for track_id, track in tracks.items():
            score, details = match_score(segment, track, args.max_centroid_distance)
            valid = details["overlap"] >= args.min_voxel_overlap or (
                details["distance"] <= args.max_centroid_distance
                and details["semantic"] >= args.min_semantic_similarity
            )
            if valid and score >= args.min_match_score:
                candidate_pairs.append((score, segment_index, track_id))
                diagnostics[(segment_index, track_id)] = details

    assignments: dict[int, tuple[int, float]] = {}
    used_segments: set[int] = set()
    used_tracks: set[int] = set()
    for score, segment_index, track_id in sorted(candidate_pairs, reverse=True):
        if segment_index in used_segments or track_id in used_tracks:
            continue
        segment = segments[segment_index]
        assignments[segment.local_id] = (track_id, score)
        used_segments.add(segment_index)
        used_tracks.add(track_id)
        update_track(tracks[track_id], segment, frame_index, args.max_track_voxels)

    for segment_index, segment in enumerate(segments):
        if segment_index in used_segments:
            continue
        track_id = next_track_id
        next_track_id += 1
        tracks[track_id] = Track(
            track_id=track_id,
            centroid=segment.centroid.copy(),
            descriptor=segment.descriptor.copy(),
        )
        update_track(tracks[track_id], segment, frame_index, args.max_track_voxels)
        assignments[segment.local_id] = (track_id, 0.50)
    return assignments, next_track_id


def palette_color(label: int) -> np.ndarray:
    if label == 0:
        return np.asarray([0, 0, 0], dtype=np.uint8)
    return np.asarray(
        [(37 * label + 53) % 255, (97 * label + 101) % 255, (17 * label + 191) % 255],
        dtype=np.uint8,
    )


def save_qa_sheet(dataset: Path, output_dir: Path, frames: list[dict], cols: int = 10) -> Path:
    thumb_w, thumb_h, label_h = 192, 144, 20
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, frame in enumerate(frames):
        stem = Path(frame["image"]).stem
        image = np.asarray(Image.open(dataset / frame["image"]).convert("RGB"))
        labels = np.asarray(Image.open(output_dir / f"{stem}.png"), dtype=np.int32)
        colors = np.zeros_like(image)
        for label in np.unique(labels):
            colors[labels == label] = palette_color(int(label))
        overlay = image.copy()
        foreground = labels > 0
        overlay[foreground] = (0.55 * image[foreground] + 0.45 * colors[foreground]).astype(np.uint8)
        resampling = getattr(Image, "Resampling", Image)
        thumb = Image.fromarray(overlay).resize((thumb_w, thumb_h), resampling.BILINEAR)
        thumb_draw = ImageDraw.Draw(thumb)
        scale_x = thumb_w / labels.shape[1]
        scale_y = thumb_h / labels.shape[0]
        for label in np.unique(labels):
            if label == 0:
                continue
            rows_for_label, cols_for_label = np.nonzero(labels == label)
            if len(rows_for_label) < 100:
                continue
            tx = int(np.median(cols_for_label) * scale_x)
            ty = int(np.median(rows_for_label) * scale_y)
            text = str(int(label))
            thumb_draw.rectangle((tx - 2, ty - 2, tx + 7 * len(text), ty + 10), fill="black")
            thumb_draw.text((tx, ty - 1), text, fill="white")
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill="black")
        draw.text((x + 4, y + thumb_h + 3), stem, fill="white")
    path = dataset / "object_mask_rgbd_report" / "object_mask_rgbd_contact_sheet.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=92)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output_dir", default="object_mask_rgbd")
    parser.add_argument("--confidence_dir", default="object_confidence_rgbd")
    parser.add_argument("--mask_level", type=int, default=0)
    parser.add_argument("--min_area", type=int, default=180)
    parser.add_argument("--max_area_ratio", type=float, default=0.45)
    parser.add_argument("--min_depth", type=float, default=0.2)
    parser.add_argument("--max_depth", type=float, default=4.0)
    parser.add_argument("--voxel_size", type=float, default=0.04)
    parser.add_argument("--max_segment_points", type=int, default=1024)
    parser.add_argument("--max_track_voxels", type=int, default=12000)
    parser.add_argument("--min_voxel_overlap", type=float, default=0.025)
    parser.add_argument("--max_centroid_distance", type=float, default=0.16)
    parser.add_argument("--min_semantic_similarity", type=float, default=0.72)
    parser.add_argument("--min_match_score", type=float, default=0.30)
    parser.add_argument("--min_track_frames", type=int, default=2)
    parser.add_argument("--max_tracks", type=int, default=255)
    args = parser.parse_args()

    dataset = args.dataset.expanduser().resolve()
    metadata = json.loads((dataset / "rgbd_metadata.json").read_text(encoding="utf-8"))
    frames = metadata["frames"]
    intrinsics = metadata["intrinsics"]
    depth_factor = float(metadata["depth_factor"])
    output_dir = dataset / args.output_dir
    confidence_dir = dataset / args.confidence_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    confidence_dir.mkdir(parents=True, exist_ok=True)

    tracks: dict[int, Track] = {}
    next_track_id = 1
    frame_records: list[dict] = []
    for frame_index, frame in enumerate(frames):
        seg_map, segments = load_segments(
            dataset, frame, args.mask_level, args.min_area, args.max_area_ratio,
            args.min_depth, args.max_depth, args.max_segment_points,
            args.voxel_size, intrinsics, depth_factor,
        )
        assignments, next_track_id = associate_frame(
            segments, tracks, frame_index, next_track_id, args
        )
        frame_records.append({
            "frame_index": frame_index,
            "stem": Path(frame["image"]).stem,
            "seg_map": seg_map,
            "assignments": assignments,
            "segment_count": len(segments),
        })
        print(
            f"[{frame_index + 1:03d}/{len(frames):03d}] "
            f"segments={len(segments):3d} tracks={len(tracks):4d}"
        )

    eligible_tracks = [
        track for track in tracks.values() if len(track.frame_indices) >= args.min_track_frames
    ]
    eligible_tracks.sort(key=lambda track: (-len(track.frame_indices), -track.total_area, track.track_id))
    eligible_tracks = eligible_tracks[: args.max_tracks]
    output_ids = {track.track_id: index + 1 for index, track in enumerate(eligible_tracks)}

    for record in frame_records:
        seg_map = record.pop("seg_map")
        labels = np.zeros(seg_map.shape, dtype=np.uint8)
        confidence = np.full(seg_map.shape, 255, dtype=np.uint8)
        for local_id, (track_id, score) in record["assignments"].items():
            output_id = output_ids.get(track_id)
            if output_id is None:
                continue
            mask = seg_map == local_id
            labels[mask] = output_id
            confidence[mask] = int(np.clip(score, 0.25, 1.0) * 255)
        Image.fromarray(labels).save(output_dir / f"{record['stem']}.png")
        Image.fromarray(confidence).save(confidence_dir / f"{record['stem']}.png")
        record["assignments"] = {
            str(local_id): {
                "internal_track_id": track_id,
                "output_id": output_ids.get(track_id, 0),
                "confidence": float(score),
            }
            for local_id, (track_id, score) in record["assignments"].items()
        }

    report_dir = dataset / "object_mask_rgbd_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    parameters = vars(args).copy()
    parameters["dataset"] = str(args.dataset)
    report = {
        "dataset": str(dataset),
        "parameters": parameters,
        "raw_track_count": len(tracks),
        "saved_track_count": len(eligible_tracks),
        "tracks": [
            {
                "output_id": output_ids[track.track_id],
                "internal_track_id": track.track_id,
                "frame_count": len(track.frame_indices),
                "frames": sorted(track.frame_indices),
                "total_area": track.total_area,
                "observations": track.observations,
                "centroid_world_m": track.centroid.tolist(),
            }
            for track in eligible_tracks
        ],
        "frames": frame_records,
    }
    report_path = report_dir / "object_mask_rgbd_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    sheet_path = save_qa_sheet(dataset, output_dir, frames)
    print(json.dumps({
        "output_dir": str(output_dir),
        "confidence_dir": str(confidence_dir),
        "raw_tracks": len(tracks),
        "saved_tracks": len(eligible_tracks),
        "report": str(report_path),
        "contact_sheet": str(sheet_path),
    }, indent=2))


if __name__ == "__main__":
    main()
