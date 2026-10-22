import os
from argparse import ArgumentParser

import numpy as np
import open_clip as clip
import torch
from PIL import Image


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


def get_queries_for_dataset(model_path):
    norm = model_path.replace("\\", "/")
    for dataset_name, queries in DATASET_TEXT_QUERIES.items():
        if f"/{dataset_name}" in norm or norm.endswith(dataset_name):
            print(f"Dataset '{dataset_name}' detected. Using official-eval text queries.")
            return queries
    print("Warning: Could not detect a known dataset name in the model path.")
    return None


def available_indices(decoded_path, logits_path):
    decoded_indices = set()
    logits_indices = set()

    if os.path.isdir(decoded_path):
        for name in os.listdir(decoded_path):
            if name.startswith("decoded_") and name.endswith(".npy"):
                decoded_indices.add(int(name.replace("decoded_", "").replace(".npy", "")))
    if os.path.isdir(logits_path):
        for name in os.listdir(logits_path):
            if name.endswith("_logits.npy"):
                logits_indices.add(int(name.split("_")[0]))

    return sorted(decoded_indices & logits_indices)


def generate_masks(model_path, text_queries, clip_checkpoint=None):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    base_path = os.path.join(model_path, "test", "ours_30000_text")
    decoded_path = os.path.join(base_path, "feature_map_npy", "decoded")
    logits_path = os.path.join(base_path, "logits")
    save_base_path = os.path.join(base_path, "test_mask")

    indices = available_indices(decoded_path, logits_path)
    if not indices:
        raise FileNotFoundError(
            f"No matching decoded/logits files found under {decoded_path} and {logits_path}. "
            "Run feature_projector.py first."
        )

    pretrained = clip_checkpoint or "laion2b_s34b_b88k"
    if clip_checkpoint and not os.path.isfile(clip_checkpoint):
        raise FileNotFoundError(f"Local OpenCLIP checkpoint not found: {clip_checkpoint}")
    model, _, _ = clip.create_model_and_transforms(
        "ViT-B-16", pretrained=pretrained, precision="fp32"
    )
    model.eval().to(device)

    d = 1
    neighbor_offsets = [
        (dy, dx)
        for dy in range(-d, d + 1)
        for dx in range(-d, d + 1)
        if not (dy == 0 and dx == 0)
    ]

    for idx in indices:
        print(f"\n--- Processing image index: {idx} ---")
        decoded_feature_map = np.load(os.path.join(decoded_path, f"decoded_{idx:05d}.npy"))
        logits = np.load(os.path.join(logits_path, f"{idx:05d}_logits.npy"))

        height, width, channels = decoded_feature_map.shape
        decoded_feature_tensor = torch.from_numpy(decoded_feature_map).float().to(device)
        logits_tensor = torch.from_numpy(logits).long().to(device)

        decoded_feature_flattened = decoded_feature_tensor.view(-1, channels)
        decoded_feature_flattened = decoded_feature_flattened / decoded_feature_flattened.norm(
            dim=-1, keepdim=True
        )

        id_values = torch.unique(logits_tensor)
        save_path = os.path.join(save_base_path, str(idx))
        os.makedirs(save_path, exist_ok=True)

        id_to_mask = {val.item(): (logits_tensor == val).cpu().numpy() for val in id_values}
        adjacency = {val.item(): set() for val in id_values}
        unique_ids = [val.item() for val in id_values]

        for i in range(len(unique_ids)):
            id_a = unique_ids[i]
            mask_a = id_to_mask[id_a]
            for j in range(i + 1, len(unique_ids)):
                id_b = unique_ids[j]
                mask_b = id_to_mask[id_b]
                found_neighbor = False
                for dy, dx in neighbor_offsets:
                    shifted_a = np.roll(mask_a, shift=(dy, dx), axis=(0, 1))
                    if np.logical_and(shifted_a, mask_b).any():
                        found_neighbor = True
                        break
                if found_neighbor:
                    adjacency[id_a].add(id_b)
                    adjacency[id_b].add(id_a)

        for input_text in text_queries:
            text_tokens = clip.tokenize([input_text]).to(device)
            with torch.no_grad():
                text_feature = model.encode_text(text_tokens).float()
            text_feature = text_feature / text_feature.norm(dim=-1, keepdim=True)

            cosine_similarity = torch.matmul(decoded_feature_flattened, text_feature.T).squeeze()
            cosine_similarity = cosine_similarity.view(height, width)

            id_avg_similarity = {}
            for id_value in id_values:
                mask_id = logits_tensor == id_value
                if mask_id.sum() == 0:
                    continue
                sim_vals = cosine_similarity[mask_id]
                if sim_vals.numel() > 0:
                    top_k = int(0.7 * sim_vals.numel())
                    top_vals = torch.topk(sim_vals, top_k).values if top_k > 0 else sim_vals
                    id_avg_similarity[id_value.item()] = (
                        top_vals.mean().item() if top_vals.numel() > 0 else 0
                    )
                else:
                    id_avg_similarity[id_value.item()] = 0

            if not id_avg_similarity:
                continue

            sorted_ids = sorted(id_avg_similarity.items(), key=lambda item: item[1], reverse=True)
            best_id = sorted_ids[0][0]

            visited = set()
            queue = [best_id]
            threshold_ratio = 0.1

            while queue:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                current_sim = id_avg_similarity[current_id]

                for neighbor_id in adjacency[current_id]:
                    if neighbor_id in visited:
                        continue
                    neighbor_sim = id_avg_similarity[neighbor_id]
                    if current_sim > 0 and abs(neighbor_sim - current_sim) <= threshold_ratio * current_sim:
                        queue.append(neighbor_id)
                    elif current_sim == 0 and neighbor_sim == 0:
                        queue.append(neighbor_id)

            mask = torch.zeros_like(logits_tensor, dtype=torch.uint8)
            for id_val in visited:
                mask[logits_tensor == id_val] = 255

            mask_filename = os.path.join(save_path, f"{input_text}.png")
            Image.fromarray(mask.cpu().numpy().astype(np.uint8)).save(mask_filename)
            print(f"  Saved mask for '{input_text}'")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Official ILGS mask expansion with evaluation-compatible queries and file names."
    )
    parser.add_argument("-m", "--model_path", type=str, required=True)
    parser.add_argument(
        "--clip_checkpoint",
        type=str,
        default=os.environ.get("OPEN_CLIP_CHECKPOINT", ""),
        help="Optional local open_clip_pytorch_model.bin; avoids network access.",
    )
    args = parser.parse_args()

    queries = get_queries_for_dataset(args.model_path)
    if not queries:
        raise ValueError("Could not determine which text queries to use.")

    generate_masks(args.model_path, queries, args.clip_checkpoint or None)
    print("\nMask generation complete.")
