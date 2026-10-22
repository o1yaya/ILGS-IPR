import os
import json
from argparse import ArgumentParser

import numpy as np
import open_clip as clip
import torch
import torch.nn.functional as F
from PIL import Image

from autoencoder.model import Autoencoder


DATASET_TEXT_QUERIES = {
    "ramen": [
        "chopsticks",
        "egg",
        "glass of water",
        "pork belly",
        "wavy noodles in bowl",
        "yellow bowl",
    ],
    "figurines": [
        "green apple",
        "green toy chair",
        "old camera",
        "porcelain hand",
        "red apple",
        "red toy chair",
        "rubber duck with red hat",
    ],
    "teatime": [
        "apple",
        "bag of cookies",
        "coffee mug",
        "cookies on a plate",
        "paper napkin",
        "plate",
        "sheep",
        "spoon handle",
        "stuffed bear",
        "tea in a glass",
    ],
}


def get_dataset_name(model_path):
    norm = model_path.replace("\\", "/")
    for name in DATASET_TEXT_QUERIES:
        if f"/{name}" in norm or norm.endswith(name):
            return name
    return None


def load_text_features(text_queries, device, checkpoint=None):
    pretrained = checkpoint or "laion2b_s34b_b88k"
    if checkpoint and not os.path.isfile(checkpoint):
        raise FileNotFoundError(f"OpenCLIP checkpoint not found: {checkpoint}")
    model, _, _ = clip.create_model_and_transforms(
        "ViT-B-16", pretrained=pretrained, precision="fp32"
    )
    model.eval().to(device)

    tokens = clip.tokenize(text_queries).to(device)
    with torch.no_grad():
        text_features = model.encode_text(tokens).float()
        text_features = F.normalize(text_features, dim=-1)
    return text_features


def load_autoencoder(dataset_name, device, checkpoint=None):
    if checkpoint:
        ckpt_path = checkpoint
    elif dataset_name in DATASET_TEXT_QUERIES:
        ckpt_path = os.path.join("autoencoder", "ckpt", "lerf", dataset_name, "best_ckpt.pth")
    else:
        ckpt_path = os.path.join("autoencoder", "ckpt", dataset_name, "best_ckpt.pth")
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Autoencoder checkpoint not found: {ckpt_path}")

    encoder_hidden_dims = [256, 128, 64, 32, 3]
    decoder_hidden_dims = [16, 32, 64, 128, 256, 256, 512]
    autoencoder = Autoencoder(encoder_hidden_dims, decoder_hidden_dims).to(device)
    autoencoder.load_state_dict(torch.load(ckpt_path, map_location=device))
    autoencoder.eval()
    return autoencoder


def decode_similarity_maps(feature_path, autoencoder, text_features, device, chunk_size):
    feature_map = np.load(feature_path, mmap_mode="r")
    if feature_map.ndim != 3 or feature_map.shape[0] != 3:
        raise ValueError(f"Expected feature map shape (3,H,W), got {feature_map.shape}")

    _, height, width = feature_map.shape
    num_pixels = height * width
    num_queries = text_features.shape[0]
    sims_flat = np.empty((num_pixels, num_queries), dtype=np.float32)
    feature_flat = feature_map.reshape(3, -1)

    with torch.no_grad():
        for start in range(0, num_pixels, chunk_size):
            end = min(start + chunk_size, num_pixels)
            chunk_np = np.array(feature_flat[:, start:end].T, dtype=np.float32, copy=True)
            chunk = torch.from_numpy(chunk_np).to(device)
            decoded = autoencoder.decode(chunk).float()
            decoded = F.normalize(decoded, dim=-1)
            sims = decoded @ text_features.T
            sims_flat[start:end] = sims.cpu().numpy()

    return sims_flat.reshape(height, width, num_queries)


def build_adjacency(logits, legacy_wrap=False):
    unique_ids = np.unique(logits).astype(np.int64)
    adjacency = {int(i): set() for i in unique_ids}
    height, width = logits.shape

    offsets = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]
    if legacy_wrap:
        for dy, dx in offsets:
            shifted = np.roll(logits, shift=(dy, dx), axis=(0, 1))
            diff = logits != shifted
            if not np.any(diff):
                continue
            pairs = np.stack((logits[diff], shifted[diff]), axis=1)
            for id_a, id_b in np.unique(pairs, axis=0):
                id_a = int(id_a)
                id_b = int(id_b)
                adjacency[id_a].add(id_b)
                adjacency[id_b].add(id_a)
        return adjacency

    for dy, dx in offsets:
        y0_a = max(0, dy)
        y1_a = height + min(0, dy)
        x0_a = max(0, dx)
        x1_a = width + min(0, dx)
        y0_b = max(0, -dy)
        y1_b = height - max(0, dy)
        x0_b = max(0, -dx)
        x1_b = width - max(0, dx)

        a = logits[y0_a:y1_a, x0_a:x1_a]
        b = logits[y0_b:y1_b, x0_b:x1_b]
        diff = a != b
        if not np.any(diff):
            continue
        pairs = np.stack((a[diff], b[diff]), axis=1)
        for id_a, id_b in np.unique(pairs, axis=0):
            id_a = int(id_a)
            id_b = int(id_b)
            adjacency[id_a].add(id_b)
            adjacency[id_b].add(id_a)

    return adjacency


def top_fraction_mean(values, fraction):
    if values.size == 0:
        return 0.0
    k = max(1, int(fraction * values.size))
    if k >= values.size:
        return float(values.mean())
    top = np.partition(values, values.size - k)[values.size - k :]
    return float(top.mean())


def compute_id_similarity(sim_map, logits, unique_ids):
    scores = {}
    for id_value in unique_ids:
        mask = logits == id_value
        scores[int(id_value)] = top_fraction_mean(sim_map[mask], 0.7)
    return scores


def grow_mask(id_scores, adjacency, logits, mode, threshold_ratio):
    sorted_ids = sorted(id_scores.items(), key=lambda item: item[1], reverse=True)
    if not sorted_ids:
        return np.zeros_like(logits, dtype=np.uint8)

    best_id = sorted_ids[0][0]
    if mode == "seed_ref":
        for id_value, _ in sorted_ids:
            if id_value != 0:
                best_id = id_value
                break

    visited = set()
    queue = [best_id]
    seed_sim = id_scores[best_id]

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        current_sim = id_scores[current_id]

        for neighbor_id in adjacency[current_id]:
            if neighbor_id in visited:
                continue
            if mode == "seed_ref" and neighbor_id == 0:
                continue

            neighbor_sim = id_scores[neighbor_id]
            reference_sim = seed_sim if mode == "seed_ref" else current_sim
            if reference_sim > 0:
                if abs(neighbor_sim - reference_sim) <= threshold_ratio * abs(reference_sim):
                    queue.append(neighbor_id)
            elif neighbor_sim == 0:
                queue.append(neighbor_id)

    mask = np.zeros_like(logits, dtype=np.uint8)
    for id_value in visited:
        mask[logits == id_value] = 255
    return mask


def generate_masks(
    model_path,
    dataset_name,
    text_queries,
    mode,
    chunk_size,
    clip_checkpoint=None,
    autoencoder_checkpoint=None,
    output_dir=None,
    render_split="test",
    frame_map_path=None,
    frame_file=None,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base_path = os.path.join(model_path, render_split, "ours_30000_text")
    feature_dir = os.path.join(base_path, "feature_map_npy")
    logits_dir = os.path.join(base_path, "logits")
    save_base_path = output_dir or os.path.join(base_path, "test_mask")
    frame_names = {}
    if frame_map_path:
        with open(frame_map_path, "r", encoding="utf-8") as f:
            frame_names = {str(key): str(value) for key, value in json.load(f).items()}
    selected_frames = None
    if frame_file:
        with open(frame_file, "r", encoding="utf-8") as f:
            selected_frames = {
                line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")
            }

    autoencoder = load_autoencoder(dataset_name, device, autoencoder_checkpoint)
    text_features = load_text_features(text_queries, device, clip_checkpoint)

    logit_files = sorted(f for f in os.listdir(logits_dir) if f.endswith("_logits.npy"))
    indices = [int(f.split("_")[0]) for f in logit_files]
    threshold_ratio = 0.03 if mode == "seed_ref" else 0.10

    for idx in indices:
        frame_key = f"{idx:05d}"
        frame_name = frame_names.get(frame_key, str(idx))
        if selected_frames is not None and frame_name not in selected_frames:
            continue
        print(f"\n--- Processing image index: {idx} ---")
        feature_path = os.path.join(feature_dir, f"{idx:05d}.npy")
        logits_path = os.path.join(logits_dir, f"{idx:05d}_logits.npy")
        if not os.path.exists(feature_path) or not os.path.exists(logits_path):
            print(f"Warning: Files for index {idx} not found. Skipping.")
            continue

        logits = np.load(logits_path).astype(np.int64)
        similarity_maps = decode_similarity_maps(
            feature_path, autoencoder, text_features, device, chunk_size
        )
        unique_ids = np.unique(logits)
        adjacency = build_adjacency(logits, legacy_wrap=(mode == "official"))

        save_path = os.path.join(save_base_path, frame_name)
        os.makedirs(save_path, exist_ok=True)

        for query_id, input_text in enumerate(text_queries):
            sim_map = similarity_maps[:, :, query_id]
            id_scores = compute_id_similarity(sim_map, logits, unique_ids)
            mask = grow_mask(id_scores, adjacency, logits, mode, threshold_ratio)
            mask_filename = os.path.join(save_path, f"{input_text}.png")
            Image.fromarray(mask).save(mask_filename)
            print(f"  Saved mask for '{input_text}'")


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate masks without saving decoded 512D maps.")
    parser.add_argument("-m", "--model_path", type=str, required=True)
    parser.add_argument(
        "--mode",
        type=str,
        default="seed_ref",
        choices=["official", "seed_ref"],
        help="official reproduces current-sim expansion; seed_ref uses anti-drift expansion.",
    )
    parser.add_argument("--chunk_size", type=int, default=65536)
    parser.add_argument(
        "--dataset_name",
        default=None,
        help="Dataset key used to locate autoencoder/ckpt/<dataset_name>/best_ckpt.pth.",
    )
    parser.add_argument(
        "--query_file",
        default=None,
        help="Text file containing one evaluation query per line.",
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        default=None,
        help="Explicit evaluation queries. Overrides --query_file and built-in LERF queries.",
    )
    parser.add_argument(
        "--autoencoder_checkpoint",
        default=None,
        help="Explicit autoencoder checkpoint path.",
    )
    parser.add_argument(
        "--clip_checkpoint",
        default=os.environ.get("OPENCLIP_CHECKPOINT"),
        help="Local ViT-B-16 OpenCLIP checkpoint. Defaults to OPENCLIP_CHECKPOINT or online lookup.",
    )
    parser.add_argument(
        "--output_dir",
        default=None,
        help="Optional mask output directory. Defaults to <model>/test/ours_30000_text/test_mask.",
    )
    parser.add_argument(
        "--render_split",
        choices=["train", "test"],
        default="test",
        help="Rendered camera split to decode. Defaults to test for backward compatibility.",
    )
    parser.add_argument(
        "--frame_map",
        default=None,
        help="Optional frame_names.json; mapped frame names are used as mask subdirectories.",
    )
    parser.add_argument(
        "--frame_file",
        default=None,
        help="Optional file containing mapped frame names to decode, one per line.",
    )
    args = parser.parse_args()

    dataset_name = args.dataset_name or get_dataset_name(args.model_path)
    if dataset_name is None:
        raise ValueError(
            f"Could not infer dataset name from model path: {args.model_path}. "
            "Provide --dataset_name."
        )

    if args.queries:
        text_queries = args.queries
    elif args.query_file:
        with open(args.query_file, "r", encoding="utf-8") as f:
            text_queries = [
                line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")
            ]
    elif dataset_name in DATASET_TEXT_QUERIES:
        text_queries = DATASET_TEXT_QUERIES[dataset_name]
    else:
        raise ValueError("No queries found. Provide --query_file or --queries.")
    if not text_queries:
        raise ValueError("The query list is empty.")

    print(f"Dataset '{dataset_name}' detected.")
    print(f"Mode: {args.mode}")
    generate_masks(
        args.model_path,
        dataset_name,
        text_queries,
        args.mode,
        args.chunk_size,
        args.clip_checkpoint,
        args.autoencoder_checkpoint,
        args.output_dir,
        args.render_split,
        args.frame_map,
        args.frame_file,
    )
    print("\nMask generation complete.")
