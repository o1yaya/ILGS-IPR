import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import open_clip as clip
import torch
import torch.nn.functional as F
from PIL import Image

from segmentation_mask_stream import DATASET_TEXT_QUERIES


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}


def infer_dataset_name(dataset_path):
    norm = str(dataset_path).replace("\\", "/")
    for name in DATASET_TEXT_QUERIES:
        if norm.endswith(f"/{name}") or f"/{name}/" in norm:
            return name
    return None


def read_label(path):
    return np.array(Image.open(path))


def save_label(path, label):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(label.astype(np.uint8)).save(path)


def read_confidence(path, shape):
    if path is None or not path.exists():
        return np.ones(shape, dtype=np.float32)
    confidence = np.array(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    if confidence.shape != shape:
        confidence = np.array(Image.fromarray((confidence * 255).astype(np.uint8)).resize(shape[::-1], Image.NEAREST))
        confidence = confidence.astype(np.float32) / 255.0
    return confidence


def save_confidence(path, confidence):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(confidence * 255.0, 0, 255).astype(np.uint8)).save(path)


def find_image(mask_path, image_dir):
    for ext in IMAGE_EXTS:
        candidate = image_dir / f"{mask_path.stem}{ext}"
        if candidate.exists():
            return candidate
    matches = sorted(image_dir.glob(f"{mask_path.stem}.*"))
    for candidate in matches:
        if candidate.suffix.lower() in IMAGE_EXTS:
            return candidate
    return None


def confidence_path_for(mask_path, conf_dir):
    if conf_dir is None:
        return None
    for ext in IMAGE_EXTS:
        candidate = conf_dir / f"{mask_path.stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def load_queries(args, dataset_name):
    if args.queries:
        return args.queries
    if args.query_file:
        queries = []
        for line in Path(args.query_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
        return queries
    if dataset_name in DATASET_TEXT_QUERIES:
        return DATASET_TEXT_QUERIES[dataset_name]
    raise ValueError("Could not infer queries. Provide --queries or --query_file.")


def load_clip(device, checkpoint=None):
    pretrained = checkpoint or "laion2b_s34b_b88k"
    if checkpoint and not Path(checkpoint).is_file():
        raise FileNotFoundError(f"OpenCLIP checkpoint not found: {checkpoint}")
    model, _, preprocess = clip.create_model_and_transforms(
        "ViT-B-16", pretrained=pretrained, precision="fp32"
    )
    model.eval().to(device)
    return model, preprocess


def text_features(model, queries, device):
    tokens = clip.tokenize(queries).to(device)
    with torch.no_grad():
        features = model.encode_text(tokens).float()
        features = F.normalize(features, dim=-1)
    return features


def crop_object(image, ys, xs, bbox, padding, masked_crop, background):
    x0, y0, x1, y1 = bbox
    width, height = image.size
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(width, x1 + padding)
    y1 = min(height, y1 + padding)

    crop = image.crop((x0, y0, x1, y1)).convert("RGB")
    if not masked_crop:
        return crop

    local_mask = np.zeros((y1 - y0, x1 - x0), dtype=bool)
    inside = (ys >= y0) & (ys < y1) & (xs >= x0) & (xs < x1)
    local_mask[ys[inside] - y0, xs[inside] - x0] = True
    crop_arr = np.array(crop)
    if background == "mean":
        if local_mask.any():
            fill = crop_arr[local_mask].mean(axis=0).astype(np.uint8)
        else:
            fill = np.array([127, 127, 127], dtype=np.uint8)
    elif background == "white":
        fill = np.array([255, 255, 255], dtype=np.uint8)
    else:
        fill = np.array([0, 0, 0], dtype=np.uint8)
    crop_arr[~local_mask] = fill
    return Image.fromarray(crop_arr)


def connected_components(mask):
    from scipy import ndimage

    components, count = ndimage.label(mask)
    for component_id in range(1, count + 1):
        component = components == component_id
        area = int(component.sum())
        if area <= 0:
            continue
        ys, xs = np.nonzero(component)
        yield ys.astype(np.int32), xs.astype(np.int32), area, [
            int(xs.min()),
            int(ys.min()),
            int(xs.max()) + 1,
            int(ys.max()) + 1,
        ]


def collect_instances(mask_paths, image_dir, conf_dir, min_area, max_crops_per_id, ignore_ids):
    instances_by_id = defaultdict(list)
    labels = {}
    confidences = {}

    for mask_path in mask_paths:
        image_path = find_image(mask_path, image_dir)
        if image_path is None:
            raise FileNotFoundError(f"No matching image found for {mask_path.name} in {image_dir}")
        label = read_label(mask_path)
        confidence = read_confidence(confidence_path_for(mask_path, conf_dir), label.shape)
        labels[mask_path.name] = label
        confidences[mask_path.name] = confidence

        for object_id in sorted(int(x) for x in np.unique(label)):
            if object_id in ignore_ids:
                continue
            mask = label == object_id
            for ys, xs, area, bbox in connected_components(mask):
                if area < min_area:
                    continue
                x0, y0, x1, y1 = bbox
                instances_by_id[object_id].append(
                    {
                        "image": mask_path.name,
                        "image_path": str(image_path),
                        "object_id": object_id,
                        "area": area,
                        "area_ratio": float(area) / float(label.size),
                        "bbox": bbox,
                        "ys": ys,
                        "xs": xs,
                    }
                )

    for object_id, instances in list(instances_by_id.items()):
        instances.sort(key=lambda x: x["area"], reverse=True)

    return labels, confidences, instances_by_id


def visibility_scores(areas, sigma, min_weight):
    areas = np.asarray(areas, dtype=np.float32)
    if areas.size == 0:
        return np.zeros((0,), dtype=np.float32), 0.0
    area_median = float(np.median(areas))
    sigma = max(float(sigma), 1e-6)
    raw = areas * np.exp(-((np.sqrt(areas) - np.sqrt(max(area_median, 1e-6))) ** 2) / (2.0 * sigma * sigma))
    if float(raw.max()) <= 0:
        normalized = np.ones_like(raw, dtype=np.float32)
    else:
        normalized = raw / float(raw.max())
    normalized = np.clip(normalized, min_weight, 1.0).astype(np.float32)
    return normalized, area_median


def area_only_semantics(instances_by_id, args):
    """Build query-free object metadata for the large-region area prior."""
    semantic = {}
    for object_id, instances in instances_by_id.items():
        if not instances:
            continue
        area_ratios = np.asarray([x["area_ratio"] for x in instances], dtype=np.float32)
        area_median_ratio = float(np.median(area_ratios))
        area_p90_ratio = float(np.percentile(area_ratios, 90))
        area_max_ratio = float(area_ratios.max())
        is_large_mixed_region = (
            area_median_ratio >= args.max_semantic_area_ratio
            or area_p90_ratio >= args.max_semantic_area_ratio_p90
            or area_max_ratio >= args.max_semantic_area_ratio_max
        )
        canonical_label = (
            "__large_mixed_region__"
            if args.ignore_large_regions and is_large_mixed_region
            else "__area_only__"
        )
        semantic[str(object_id)] = {
            "canonical_label": canonical_label,
            "semantic_confidence": 1.0,
            "semantic_margin": 1.0,
            "num_crops": 0,
            "area_median": float(np.median([x["area"] for x in instances])),
            "area_median_ratio": area_median_ratio,
            "area_p90_ratio": area_p90_ratio,
            "area_max_ratio": area_max_ratio,
            "top_labels": [],
            "crops": [],
            "reason": (
                "large mixed/background region detected from component area statistics"
                if canonical_label == "__large_mixed_region__"
                else "query-free area-only prior"
            ),
        }
    return semantic


def score_crops(model, preprocess, text_feats, queries, instances_by_id, args, device):
    semantic = {}
    crop_rows = []
    image_cache = {}

    for object_id, instances_all in instances_by_id.items():
        if not instances_all:
            continue
        area_ratios = np.asarray([x["area_ratio"] for x in instances_all], dtype=np.float32)
        area_median_ratio = float(np.median(area_ratios))
        area_p90_ratio = float(np.percentile(area_ratios, 90))
        area_max_ratio = float(area_ratios.max())
        is_large_mixed_region = (
            area_median_ratio >= args.max_semantic_area_ratio
            or area_p90_ratio >= args.max_semantic_area_ratio_p90
            or area_max_ratio >= args.max_semantic_area_ratio_max
        )
        if args.ignore_large_regions and is_large_mixed_region:
            semantic[str(object_id)] = {
                "canonical_label": "__large_mixed_region__",
                "semantic_confidence": 0.0,
                "semantic_margin": 0.0,
                "num_crops": 0,
                "area_median": float(np.median([x["area"] for x in instances_all])),
                "area_median_ratio": area_median_ratio,
                "area_p90_ratio": area_p90_ratio,
                "area_max_ratio": area_max_ratio,
                "top_labels": [],
                "crops": [],
                "reason": "ignored because component area distribution indicates a large mixed/background region",
            }
            continue
        instances = instances_all[:max(1, args.max_crops_per_id)] if args.max_crops_per_id > 0 else instances_all

        vis_weights, area_median = visibility_scores(
            [x["area"] for x in instances], args.visibility_sigma, args.min_visibility_weight
        )
        label_scores = np.zeros((len(queries),), dtype=np.float64)
        crop_predictions = []

        for idx, instance in enumerate(instances):
            image_path = instance["image_path"]
            if image_path not in image_cache:
                image_cache[image_path] = Image.open(image_path).convert("RGB")
            image = image_cache[image_path]
            crop_image = crop_object(
                image,
                instance["ys"],
                instance["xs"],
                instance["bbox"],
                args.crop_padding,
                args.masked_crop,
                args.mask_background,
            )
            crop_tensor = preprocess(crop_image).unsqueeze(0).to(device)
            with torch.no_grad():
                image_feat = model.encode_image(crop_tensor).float()
                image_feat = F.normalize(image_feat, dim=-1)
                sims = (image_feat @ text_feats.T).squeeze(0)
                probs = torch.softmax(sims * args.clip_softmax_scale, dim=0).cpu().numpy()
                sims_np = sims.cpu().numpy()

            top_indices = np.argsort(-probs)[: args.topk]
            visibility = float(vis_weights[idx])
            label_scores += visibility * probs
            pred = {
                "image": instance["image"],
                "area": int(instance["area"]),
                "visibility": visibility,
                "bbox": instance["bbox"],
                "top_labels": [
                    {
                        "label": queries[int(i)],
                        "prob": float(probs[int(i)]),
                        "similarity": float(sims_np[int(i)]),
                    }
                    for i in top_indices
                ],
            }
            crop_predictions.append(pred)
            crop_rows.append(
                {
                    "object_id": object_id,
                    "image": instance["image"],
                    "area": int(instance["area"]),
                    "area_ratio": float(instance["area_ratio"]),
                    "visibility": visibility,
                    "top1_label": queries[int(top_indices[0])],
                    "top1_prob": float(probs[int(top_indices[0])]),
                    "top2_label": queries[int(top_indices[1])] if len(top_indices) > 1 else "",
                    "top2_prob": float(probs[int(top_indices[1])]) if len(top_indices) > 1 else "",
                }
            )

        order = np.argsort(-label_scores)
        top1 = int(order[0])
        top2 = int(order[1]) if len(order) > 1 else top1
        total = float(label_scores.sum())
        semantic_conf = float(label_scores[top1] / total) if total > 0 else 0.0
        margin = float((label_scores[top1] - label_scores[top2]) / total) if total > 0 and top2 != top1 else semantic_conf

        semantic[str(object_id)] = {
            "canonical_label": queries[top1],
            "semantic_confidence": semantic_conf,
            "semantic_margin": margin,
            "num_crops": len(instances),
            "area_median": area_median,
            "area_median_ratio": area_median_ratio,
            "area_p90_ratio": area_p90_ratio,
            "area_max_ratio": area_max_ratio,
            "top_labels": [
                {"label": queries[int(i)], "score": float(label_scores[int(i)])}
                for i in order[: args.topk]
            ],
            "crops": crop_predictions,
        }

    return semantic, crop_rows


def score_crop_consistency(model, preprocess, instances_by_id, args, device):
    """Score each identity track by query-free cross-view CLIP consistency."""
    semantic = {}
    crop_rows = []
    image_cache = {}

    for object_id, instances_all in instances_by_id.items():
        if not instances_all:
            continue
        area_ratios = np.asarray([x["area_ratio"] for x in instances_all], dtype=np.float32)
        area_median_ratio = float(np.median(area_ratios))
        area_p90_ratio = float(np.percentile(area_ratios, 90))
        area_max_ratio = float(area_ratios.max())
        area_median = float(np.median([x["area"] for x in instances_all]))
        is_large_mixed_region = (
            area_median_ratio >= args.max_semantic_area_ratio
            or area_p90_ratio >= args.max_semantic_area_ratio_p90
            or area_max_ratio >= args.max_semantic_area_ratio_max
        )
        if args.ignore_large_regions and is_large_mixed_region:
            semantic[str(object_id)] = {
                "canonical_label": "__large_mixed_region__",
                "semantic_confidence": 0.0,
                "semantic_margin": 1.0,
                "num_crops": 0,
                "area_median": area_median,
                "area_median_ratio": area_median_ratio,
                "area_p90_ratio": area_p90_ratio,
                "area_max_ratio": area_max_ratio,
                "top_labels": [],
                "crops": [],
                "reason": "large mixed/background region detected from component area statistics",
            }
            continue

        instances = (
            instances_all[:max(1, args.max_crops_per_id)]
            if args.max_crops_per_id > 0
            else instances_all
        )
        crop_tensors = []
        for instance in instances:
            image_path = instance["image_path"]
            if image_path not in image_cache:
                image_cache[image_path] = Image.open(image_path).convert("RGB")
            crop_image = crop_object(
                image_cache[image_path],
                instance["ys"],
                instance["xs"],
                instance["bbox"],
                args.crop_padding,
                args.masked_crop,
                args.mask_background,
            )
            crop_tensors.append(preprocess(crop_image))

        with torch.no_grad():
            features = model.encode_image(torch.stack(crop_tensors).to(device)).float()
            features = F.normalize(features, dim=-1)
            prototype = F.normalize(features.mean(dim=0, keepdim=True), dim=-1)
            prototype_sims = (features @ prototype.T).squeeze(1)
            if len(instances) > 1:
                similarity = features @ features.T
                indices = torch.triu_indices(len(instances), len(instances), offset=1)
                consistency = float(similarity[indices[0], indices[1]].mean().item())
            else:
                consistency = 1.0
            prototype_sims_np = prototype_sims.cpu().numpy()

        consistency = float(np.clip(consistency, 0.0, 1.0))
        crop_predictions = []
        for instance, prototype_similarity in zip(instances, prototype_sims_np):
            prediction = {
                "image": instance["image"],
                "area": int(instance["area"]),
                "bbox": instance["bbox"],
                "prototype_similarity": float(prototype_similarity),
            }
            crop_predictions.append(prediction)
            crop_rows.append(
                {
                    "object_id": object_id,
                    "image": instance["image"],
                    "area": int(instance["area"]),
                    "area_ratio": float(instance["area_ratio"]),
                    "track_consistency": consistency,
                    "prototype_similarity": float(prototype_similarity),
                }
            )

        semantic[str(object_id)] = {
            "canonical_label": "__clip_consistent_track__",
            "semantic_confidence": consistency,
            "semantic_margin": 1.0,
            "num_crops": len(instances),
            "area_median": area_median,
            "area_median_ratio": area_median_ratio,
            "area_p90_ratio": area_p90_ratio,
            "area_max_ratio": area_max_ratio,
            "top_labels": [],
            "crops": crop_predictions,
            "reason": "query-free cross-view CLIP crop consistency",
        }

    return semantic, crop_rows


def apply_semantic_area_confidence(labels, confidences, instances_by_id, semantic, args):
    refined = {name: label.copy() for name, label in labels.items()}
    refined_conf = {name: conf.copy() for name, conf in confidences.items()}
    image_rows = []
    object_weights = {}

    for object_id, instances in instances_by_id.items():
        if not instances:
            continue
        object_key = str(object_id)
        sem = semantic.get(object_key, {})
        sem_conf = float(sem.get("semantic_confidence", 1.0))
        sem_margin = float(sem.get("semantic_margin", 1.0))
        semantic_weight = 1.0
        reason = "trusted"
        if (
            not args.disable_large_region_weight
            and sem.get("canonical_label") == "__large_mixed_region__"
        ):
            semantic_weight = args.large_region_weight
            reason = "large_mixed_region"
        elif (
            not args.disable_semantic_weight
            and sem.get("canonical_label") != "__large_mixed_region__"
            and (sem_conf < args.semantic_conf_threshold or sem_margin < args.semantic_margin_threshold)
        ):
            semantic_weight = args.low_semantic_weight
            reason = "low_semantic_confidence"
        elif args.disable_semantic_weight:
            reason = "semantic_weight_disabled"
        elif args.disable_large_region_weight and sem.get("canonical_label") == "__large_mixed_region__":
            reason = "large_region_weight_disabled"

        if args.disable_visibility_weight:
            vis_weights = np.ones((len(instances),), dtype=np.float32)
        else:
            vis_weights, _ = visibility_scores(
                [x["area"] for x in instances], args.visibility_sigma, args.min_visibility_weight
            )
        for instance, visibility in zip(instances, vis_weights):
            image_name = instance["image"]
            ys = instance["ys"]
            xs = instance["xs"]
            weight = float(visibility) * semantic_weight
            refined_conf[image_name][ys, xs] *= weight

        object_weights[object_key] = {
            "semantic_weight": semantic_weight,
            "semantic_confidence": sem_conf,
            "semantic_margin": sem_margin,
            "reason": reason,
            "mean_visibility": float(np.mean(vis_weights)) if len(vis_weights) else 1.0,
            "min_visibility": float(np.min(vis_weights)) if len(vis_weights) else 1.0,
        }

    for name in sorted(labels):
        conf = np.clip(refined_conf[name], args.min_confidence, 1.0)
        refined_conf[name] = conf
        low_conf = conf < 0.999
        image_rows.append(
            {
                "image": name,
                "pixels": int(conf.size),
                "low_confidence_pixels": int(low_conf.sum()),
                "low_confidence_ratio": float(low_conf.mean()),
            }
        )

    return refined, refined_conf, image_rows, object_weights


def cosine_from_text_features(text_feats):
    feats = text_feats.detach().cpu().numpy()
    return feats @ feats.T


def merge_candidates(semantic, queries, text_feats, args):
    query_to_index = {q: i for i, q in enumerate(queries)}
    text_cos = cosine_from_text_features(text_feats)
    items = []
    for object_id, sem in semantic.items():
        label = sem["canonical_label"]
        if label not in query_to_index:
            continue
        items.append((int(object_id), label, int(query_to_index[label]), float(sem["semantic_confidence"])))

    candidates = []
    for i in range(len(items)):
        id_a, label_a, idx_a, conf_a = items[i]
        for j in range(i + 1, len(items)):
            id_b, label_b, idx_b, conf_b = items[j]
            sim = float(text_cos[idx_a, idx_b])
            if sim < args.merge_semantic_similarity:
                continue
            if min(conf_a, conf_b) < args.merge_min_confidence:
                continue
            candidates.append(
                {
                    "object_id_a": id_a,
                    "label_a": label_a,
                    "confidence_a": conf_a,
                    "object_id_b": id_b,
                    "label_b": label_b,
                    "confidence_b": conf_b,
                    "semantic_similarity": sim,
                    "note": "candidate only; not automatically merged",
                }
            )
    candidates.sort(key=lambda x: x["semantic_similarity"], reverse=True)
    return candidates


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def refine_dataset(args):
    dataset_path = Path(args.dataset_path)
    dataset_name = args.dataset_name or infer_dataset_name(dataset_path)
    queries = (
        []
        if args.area_only or args.clip_consistency or args.semantic_json
        else load_queries(args, dataset_name)
    )

    src_dir = Path(args.src)
    if not src_dir.is_absolute():
        src_dir = dataset_path / src_dir
    image_dir = Path(args.image_dir)
    if not image_dir.is_absolute():
        image_dir = dataset_path / image_dir
    conf_src_dir = Path(args.conf_src) if args.conf_src else None
    if conf_src_dir is not None and not conf_src_dir.is_absolute():
        conf_src_dir = dataset_path / conf_src_dir
    dst_dir = Path(args.dst)
    if not dst_dir.is_absolute():
        dst_dir = dataset_path / dst_dir
    conf_dst_dir = Path(args.conf_dst)
    if not conf_dst_dir.is_absolute():
        conf_dst_dir = dataset_path / conf_dst_dir
    report_dir = Path(args.report_dir)
    if not report_dir.is_absolute():
        report_dir = dataset_path / report_dir

    mask_paths = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not mask_paths:
        raise FileNotFoundError(f"No mask images found in {src_dir}")
    if args.limit > 0:
        mask_paths = mask_paths[: args.limit]

    print(f"Dataset: {dataset_path}")
    print(f"Queries: {queries}")
    print(f"Source masks: {src_dir}")
    print(f"Images: {image_dir}")
    print(f"Source confidence: {conf_src_dir if conf_src_dir else 'none'}")

    labels, confidences, instances_by_id = collect_instances(
        mask_paths,
        image_dir,
        conf_src_dir,
        args.min_component_area,
        args.max_crops_per_id,
        {int(x) for x in args.ignore_ids},
    )

    semantic_json = Path(args.semantic_json) if args.semantic_json else None
    if semantic_json is not None and not semantic_json.is_absolute():
        semantic_json = dataset_path / semantic_json

    if args.area_only:
        semantic = area_only_semantics(instances_by_id, args)
        crop_rows = []
        candidates = []
        args.disable_semantic_weight = True
        print("Using query-free area-only object reliability; OpenCLIP is not loaded.")
    elif args.clip_consistency:
        device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        model, preprocess = load_clip(device, args.clip_checkpoint)
        semantic, crop_rows = score_crop_consistency(
            model, preprocess, instances_by_id, args, device
        )
        candidates = []
        args.semantic_conf_threshold = args.consistency_threshold
        print(
            "Using query-free cross-view CLIP consistency "
            f"(threshold={args.consistency_threshold:.3f})."
        )
    elif semantic_json is not None:
        with semantic_json.open("r", encoding="utf-8") as f:
            cached_semantic = json.load(f)
        semantic = cached_semantic["objects"]
        crop_rows = []
        candidates = []
        print(f"Using cached object semantics: {semantic_json}")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
        model, preprocess = load_clip(device, args.clip_checkpoint)
        text_feats = text_features(model, queries, device)
        semantic, crop_rows = score_crops(
            model, preprocess, text_feats, queries, instances_by_id, args, device
        )
        candidates = merge_candidates(semantic, queries, text_feats, args)

    refined, refined_conf, image_rows, object_weights = apply_semantic_area_confidence(
        labels, confidences, instances_by_id, semantic, args
    )

    if not args.confidence_only:
        dst_dir.mkdir(parents=True, exist_ok=True)
    conf_dst_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    for name in sorted(refined):
        if not args.confidence_only:
            save_label(dst_dir / Path(name).with_suffix(".png").name, refined[name])
        save_confidence(conf_dst_dir / Path(name).with_suffix(".png").name, refined_conf[name])

    semantic_out = {
        "queries": queries,
        "parameters": vars(args),
        "objects": semantic,
        "object_weights": object_weights,
    }
    with (report_dir / "object_semantics.json").open("w", encoding="utf-8") as f:
        json.dump(semantic_out, f, indent=2)
    with (report_dir / "merge_candidates.json").open("w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    write_csv(report_dir / "object_semantic_crops.csv", crop_rows)
    write_csv(report_dir / "object_semantic_area_summary.csv", image_rows)

    if args.confidence_only:
        print(f"semantic-area masks:      unchanged ({src_dir})")
    else:
        print(f"semantic-area masks:      {dst_dir}")
    print(f"semantic-area confidence: {conf_dst_dir}")
    print(f"semantic report:          {report_dir / 'object_semantics.json'}")
    print(f"merge candidates:         {report_dir / 'merge_candidates.json'}")
    print(f"crop report:              {report_dir / 'object_semantic_crops.csv'}")
    print(f"summary report:           {report_dir / 'object_semantic_area_summary.csv'}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Semantic- and area-aware refinement for ILGS object masks. "
            "This script keeps object ids unchanged by default, uses CLIP crop semantics "
            "and TrackRef3D-style visibility scores to produce object-level semantic priors "
            "and confidence-weighted pseudo labels."
        )
    )
    parser.add_argument("--dataset_path", required=True)
    parser.add_argument("--dataset_name", default=None)
    parser.add_argument("--src", default="object_mask_refined")
    parser.add_argument("--conf_src", default="object_confidence_refined")
    parser.add_argument("--image_dir", default="images")
    parser.add_argument("--dst", default="object_mask_semantic_area_refined")
    parser.add_argument("--conf_dst", default="object_confidence_semantic_area_refined")
    parser.add_argument("--report_dir", default="object_mask_semantic_area_report")
    parser.add_argument("--queries", nargs="*", default=None)
    parser.add_argument("--query_file", default=None)
    parser.add_argument(
        "--clip_checkpoint",
        default=os.environ.get("OPENCLIP_CHECKPOINT"),
        help="Local ViT-B-16 OpenCLIP checkpoint. Defaults to OPENCLIP_CHECKPOINT or online lookup.",
    )
    parser.add_argument(
        "--semantic_json",
        default=None,
        help="Reuse objects from an existing object_semantics.json instead of rerunning CLIP.",
    )
    parser.add_argument(
        "--area_only",
        action="store_true",
        help="Skip queries and OpenCLIP; apply only the component-area large-region prior.",
    )
    parser.add_argument(
        "--clip_consistency",
        action="store_true",
        help="Use query-free cross-view CLIP crop consistency as semantic reliability.",
    )
    parser.add_argument(
        "--consistency_threshold",
        type=float,
        default=0.80,
        help="Down-weight identity tracks below this mean pairwise CLIP cosine similarity.",
    )
    parser.add_argument("--ignore_ids", nargs="*", type=int, default=[])
    parser.add_argument("--min_component_area", type=int, default=500)
    parser.add_argument("--max_crops_per_id", type=int, default=40)
    parser.add_argument("--crop_padding", type=int, default=12)
    parser.add_argument("--masked_crop", action="store_true", default=True)
    parser.add_argument("--unmasked_crop", dest="masked_crop", action="store_false")
    parser.add_argument("--mask_background", choices=["mean", "white", "black"], default="mean")
    parser.add_argument("--visibility_sigma", type=float, default=100.0)
    parser.add_argument("--min_visibility_weight", type=float, default=0.25)
    parser.add_argument("--semantic_conf_threshold", type=float, default=0.45)
    parser.add_argument("--semantic_margin_threshold", type=float, default=0.08)
    parser.add_argument("--low_semantic_weight", type=float, default=0.65)
    parser.add_argument("--ignore_large_regions", action="store_true", default=True)
    parser.add_argument("--keep_large_regions", dest="ignore_large_regions", action="store_false")
    parser.add_argument("--max_semantic_area_ratio", type=float, default=0.55)
    parser.add_argument("--max_semantic_area_ratio_p90", type=float, default=0.35)
    parser.add_argument("--max_semantic_area_ratio_max", type=float, default=0.45)
    parser.add_argument("--large_region_weight", type=float, default=0.35)
    parser.add_argument(
        "--disable_semantic_weight",
        action="store_true",
        help="Do not down-weight IDs with uncertain crop semantics.",
    )
    parser.add_argument(
        "--disable_visibility_weight",
        action="store_true",
        help="Use unit per-view visibility weights for every object instance.",
    )
    parser.add_argument(
        "--disable_large_region_weight",
        action="store_true",
        help="Do not down-weight IDs detected as large mixed/background regions.",
    )
    parser.add_argument(
        "--confidence_only",
        action="store_true",
        help="Write only confidence maps and reports; keep source object masks unchanged.",
    )
    parser.add_argument("--min_confidence", type=float, default=0.05)
    parser.add_argument("--clip_softmax_scale", type=float, default=35.0)
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--merge_semantic_similarity", type=float, default=0.88)
    parser.add_argument("--merge_min_confidence", type=float, default=0.55)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    refine_dataset(parser.parse_args())


if __name__ == "__main__":
    main()
