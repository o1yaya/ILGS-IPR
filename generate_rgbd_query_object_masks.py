#!/usr/bin/env python3
"""Create a target-specific RGB-D object mask from cached ILGS SAM/CLIP features."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from build_rgbd_object_masks import normalize, quaternion_xyzw_to_rotation


@dataclass
class Candidate:
    level: int
    feature_id: int
    area: int
    text_score: float
    centroid: np.ndarray
    voxels: set
    mask: np.ndarray


def load_text_embeddings(queries, negatives, model_name, pretrained, device):
    import open_clip

    model, _, _ = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained,
        precision="fp16" if device.startswith("cuda") else "fp32",
    )
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    texts = list(queries) + list(negatives)
    tokens = tokenizer(texts).to(device)
    with torch.no_grad():
        embeddings = model.encode_text(tokens)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
    embeddings = embeddings.float().cpu().numpy()
    return embeddings[: len(queries)], embeddings[len(queries) :]


def relevancy_scores(features, positive_embeddings, negative_embeddings):
    features = features.astype(np.float32)
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    features = features / np.maximum(norms, 1e-8)
    positive = features @ positive_embeddings.T
    negative = features @ negative_embeddings.T
    alias_scores = []
    for positive_index in range(positive.shape[1]):
        difference = 10.0 * (positive[:, positive_index : positive_index + 1] - negative)
        probability = 1.0 / (1.0 + np.exp(-np.clip(difference, -50.0, 50.0)))
        alias_scores.append(probability.min(axis=1))
    return np.stack(alias_scores, axis=1).max(axis=1)


def load_candidates(dataset, frame, text_scores, metadata, args):
    stem = Path(frame["image"]).stem
    seg_maps = np.load(dataset / "language_features" / f"{stem}_s.npy").astype(np.int32)
    features = np.load(dataset / "language_features" / f"{stem}_f.npy").astype(np.float32)
    frame_scores = relevancy_scores(features, text_scores[0], text_scores[1])
    depth = np.asarray(Image.open(dataset / frame["depth"]), dtype=np.float32)
    depth /= float(metadata["depth_factor"])
    intrinsics = metadata["intrinsics"]
    fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
    cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    rotation_wc = quaternion_xyzw_to_rotation(
        np.asarray(frame["quaternion_world_from_camera_xyzw"], dtype=np.float32)
    )
    translation_wc = np.asarray(frame["translation_world_from_camera_m"], dtype=np.float32)
    height, width = depth.shape
    max_area = int(height * width * args.max_area_ratio)

    candidates = []
    for level in args.mask_levels:
        if level < 0 or level >= seg_maps.shape[0]:
            continue
        seg_map = seg_maps[level]
        feature_ids, counts = np.unique(seg_map[seg_map >= 0], return_counts=True)
        for feature_id, area in zip(feature_ids.tolist(), counts.tolist()):
            if feature_id >= len(frame_scores) or area < args.min_area or area > max_area:
                continue
            score = float(frame_scores[feature_id])
            if score < args.candidate_text_threshold:
                continue
            mask = seg_map == feature_id
            rows, cols = np.nonzero(mask)
            valid = np.isfinite(depth[rows, cols])
            valid &= depth[rows, cols] >= args.min_depth
            valid &= depth[rows, cols] <= args.max_depth
            rows, cols = rows[valid], cols[valid]
            if len(rows) < args.min_valid_depth_pixels:
                continue
            if len(rows) > args.max_segment_points:
                indices = np.linspace(0, len(rows) - 1, args.max_segment_points).astype(np.int64)
                rows, cols = rows[indices], cols[indices]
            z = depth[rows, cols]
            points_camera = np.stack(
                ((cols.astype(np.float32) - cx) * z / fx,
                 (rows.astype(np.float32) - cy) * z / fy,
                 z),
                axis=1,
            )
            points_world = points_camera @ rotation_wc.T + translation_wc
            voxel_indices = np.floor(points_world / args.voxel_size).astype(np.int32)
            voxels = set(map(tuple, voxel_indices.tolist()))
            if len(voxels) < 5:
                continue
            candidates.append(
                Candidate(
                    level=level,
                    feature_id=int(feature_id),
                    area=int(area),
                    text_score=score,
                    centroid=np.median(points_world, axis=0),
                    voxels=voxels,
                    mask=mask,
                )
            )
    return candidates


def geometry_terms(candidate, anchor_voxels, anchor_centroid, max_distance):
    intersection = len(candidate.voxels.intersection(anchor_voxels))
    overlap = intersection / max(1, len(candidate.voxels))
    distance = float(np.linalg.norm(candidate.centroid - anchor_centroid))
    distance_score = math.exp(-distance / max(max_distance, 1e-6))
    return overlap, distance, distance_score


def select_anchor_candidate(candidates, anchor_voxels, anchor_centroid, args):
    if not candidates:
        return None, 0.0, 0.0, float("inf")
    if not anchor_voxels:
        candidate = max(candidates, key=lambda item: item.text_score)
        return candidate, candidate.text_score, 0.0, 0.0
    ranked = []
    for candidate in candidates:
        overlap, distance, distance_score = geometry_terms(
            candidate, anchor_voxels, anchor_centroid, args.max_anchor_distance
        )
        score = 0.60 * candidate.text_score + 0.30 * overlap + 0.10 * distance_score
        ranked.append((score, overlap, distance, candidate))
    score, overlap, distance, candidate = max(ranked, key=lambda item: item[0])
    if overlap < args.min_anchor_overlap and distance > args.max_anchor_distance:
        return None, score, overlap, distance
    return candidate, score, overlap, distance


def expand_same_frame_mask(selected, candidates, args):
    output = selected.mask.copy()
    for candidate in candidates:
        if candidate is selected:
            continue
        if candidate.text_score < selected.text_score - args.union_text_margin:
            continue
        intersection = int(np.logical_and(selected.mask, candidate.mask).sum())
        overlap = intersection / max(1, min(selected.area, candidate.area))
        voxel_overlap = len(selected.voxels.intersection(candidate.voxels)) / max(
            1, min(len(selected.voxels), len(candidate.voxels))
        )
        if overlap >= args.union_mask_overlap or voxel_overlap >= args.union_voxel_overlap:
            output |= candidate.mask
    return output


def save_contact_sheet(dataset, output_dir, records, query_slug):
    thumb_w, thumb_h, label_h, cols = 192, 144, 20, 10
    rows = (len(records) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    resampling = getattr(Image, "Resampling", Image)
    for index, record in enumerate(records):
        image = np.asarray(Image.open(dataset / record["image"]).convert("RGB"))
        mask = np.asarray(Image.open(output_dir / f"{record['stem']}.png"), dtype=np.uint8) > 0
        overlay = image.copy()
        overlay[mask] = (0.40 * image[mask] + 0.60 * np.asarray([0, 220, 255])).astype(np.uint8)
        thumb = Image.fromarray(overlay).resize((thumb_w, thumb_h), resampling.BILINEAR)
        thumb_draw = ImageDraw.Draw(thumb)
        if mask.any():
            ys, xs = np.nonzero(mask)
            tx = int(np.median(xs) * thumb_w / mask.shape[1])
            ty = int(np.median(ys) * thumb_h / mask.shape[0])
            thumb_draw.rectangle((tx - 2, ty - 2, tx + 46, ty + 11), fill="black")
            thumb_draw.text((tx, ty - 1), f"{record['score']:.2f}", fill="white")
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), fill="black")
        draw.text((x + 4, y + thumb_h + 3), record["stem"], fill="white")
    report_dir = dataset / "query_mask_rgbd_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{query_slug}_contact_sheet.jpg"
    sheet.save(path, quality=92)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--queries", nargs="+", required=True)
    parser.add_argument("--negatives", nargs="+", default=["object", "things", "stuff", "texture"])
    parser.add_argument("--anchor_start", type=int, default=50)
    parser.add_argument("--anchor_end", type=int, default=59)
    parser.add_argument("--mask_levels", nargs="+", type=int, default=[0, 1, 2, 3])
    parser.add_argument("--output_dir", default="object_mask_query_game_controller")
    parser.add_argument("--confidence_dir", default="object_confidence_query_game_controller")
    parser.add_argument("--model_name", default="ViT-B-16")
    parser.add_argument("--pretrained", default="laion2b_s34b_b88k")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--min_area", type=int, default=150)
    parser.add_argument("--max_area_ratio", type=float, default=0.25)
    parser.add_argument("--min_depth", type=float, default=0.2)
    parser.add_argument("--max_depth", type=float, default=4.0)
    parser.add_argument("--min_valid_depth_pixels", type=int, default=20)
    parser.add_argument("--max_segment_points", type=int, default=2048)
    parser.add_argument("--voxel_size", type=float, default=0.04)
    parser.add_argument("--candidate_text_threshold", type=float, default=0.35)
    parser.add_argument("--accept_text_threshold", type=float, default=0.48)
    parser.add_argument("--min_anchor_overlap", type=float, default=0.025)
    parser.add_argument("--max_anchor_distance", type=float, default=0.25)
    parser.add_argument("--min_final_score", type=float, default=0.42)
    parser.add_argument("--union_text_margin", type=float, default=0.08)
    parser.add_argument("--union_mask_overlap", type=float, default=0.30)
    parser.add_argument("--union_voxel_overlap", type=float, default=0.20)
    parser.add_argument("--background_confidence", type=float, default=0.05)
    args = parser.parse_args()

    dataset = args.dataset.expanduser().resolve()
    metadata = json.loads((dataset / "rgbd_metadata.json").read_text(encoding="utf-8"))
    frames = metadata["frames"]
    positive_embeddings, negative_embeddings = load_text_embeddings(
        args.queries, args.negatives, args.model_name, args.pretrained, args.device
    )
    text_scores = (positive_embeddings, negative_embeddings)

    anchor_voxels = set()
    anchor_centroids = []
    anchor_records = []
    for frame_index in range(max(0, args.anchor_start), min(len(frames), args.anchor_end + 1)):
        candidates = load_candidates(dataset, frames[frame_index], text_scores, metadata, args)
        anchor_centroid = np.median(np.stack(anchor_centroids), axis=0) if anchor_centroids else np.zeros(3)
        selected, score, overlap, distance = select_anchor_candidate(
            candidates, anchor_voxels, anchor_centroid, args
        )
        if selected is None or selected.text_score < args.accept_text_threshold:
            continue
        anchor_voxels.update(selected.voxels)
        anchor_centroids.append(selected.centroid)
        anchor_records.append({
            "frame_index": frame_index,
            "feature_id": selected.feature_id,
            "level": selected.level,
            "text_score": selected.text_score,
            "combined_score": score,
            "overlap": overlap,
            "distance": distance,
        })
    if not anchor_centroids:
        raise RuntimeError("No anchor mask passed the text threshold; lower --accept_text_threshold")
    anchor_centroid = np.median(np.stack(anchor_centroids), axis=0)

    output_dir = dataset / args.output_dir
    confidence_dir = dataset / args.confidence_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    confidence_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for frame_index, frame in enumerate(frames):
        candidates = load_candidates(dataset, frame, text_scores, metadata, args)
        ranked = []
        for candidate in candidates:
            overlap, distance, distance_score = geometry_terms(
                candidate, anchor_voxels, anchor_centroid, args.max_anchor_distance
            )
            score = 0.55 * candidate.text_score + 0.35 * overlap + 0.10 * distance_score
            ranked.append((score, overlap, distance, candidate))
        selected = None
        score = overlap = 0.0
        distance = float("inf")
        if ranked:
            score, overlap, distance, candidate = max(ranked, key=lambda item: item[0])
            geometry_ok = overlap >= args.min_anchor_overlap or distance <= args.max_anchor_distance
            if (
                candidate.text_score >= args.accept_text_threshold
                and score >= args.min_final_score
                and geometry_ok
            ):
                selected = candidate

        shape = np.asarray(Image.open(dataset / frame["depth"])).shape
        mask = np.zeros(shape, dtype=np.uint8)
        confidence = np.full(
            shape,
            int(np.clip(args.background_confidence, 0.0, 1.0) * 255),
            dtype=np.uint8,
        )
        selected_level = None
        selected_feature_id = None
        text_score = 0.0
        if selected is not None:
            expanded = expand_same_frame_mask(selected, candidates, args)
            mask[expanded] = 1
            confidence[expanded] = int(np.clip(score, 0.25, 1.0) * 255)
            selected_level = selected.level
            selected_feature_id = selected.feature_id
            text_score = selected.text_score
        stem = Path(frame["image"]).stem
        Image.fromarray(mask).save(output_dir / f"{stem}.png")
        Image.fromarray(confidence).save(confidence_dir / f"{stem}.png")
        records.append({
            "frame_index": frame_index,
            "stem": stem,
            "image": frame["image"],
            "accepted": selected is not None,
            "score": float(score),
            "text_score": float(text_score),
            "voxel_overlap": float(overlap),
            "centroid_distance_m": float(distance) if math.isfinite(distance) else None,
            "level": selected_level,
            "feature_id": selected_feature_id,
            "area": int(mask.sum()),
        })
        print(
            f"[{frame_index + 1:03d}/{len(frames):03d}] accepted={selected is not None} "
            f"score={score:.3f} text={text_score:.3f} overlap={overlap:.3f}"
        )

    query_slug = "_".join(args.queries[0].lower().split())
    contact_sheet = save_contact_sheet(dataset, output_dir, records, query_slug)
    report_dir = dataset / "query_mask_rgbd_report"
    report_path = report_dir / f"{query_slug}_report.json"
    parameters = vars(args).copy()
    parameters["dataset"] = str(args.dataset)
    report_path.write_text(json.dumps({
        "queries": args.queries,
        "parameters": parameters,
        "anchor_centroid_world_m": anchor_centroid.tolist(),
        "anchor_voxel_count": len(anchor_voxels),
        "anchor_records": anchor_records,
        "accepted_frame_count": sum(record["accepted"] for record in records),
        "frames": records,
    }, indent=2), encoding="utf-8")
    print(json.dumps({
        "output_dir": str(output_dir),
        "accepted_frames": sum(record["accepted"] for record in records),
        "report": str(report_path),
        "contact_sheet": str(contact_sheet),
    }, indent=2))


if __name__ == "__main__":
    main()
