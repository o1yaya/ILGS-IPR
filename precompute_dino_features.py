import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}


def image_paths(image_dir):
    return sorted(p for p in Path(image_dir).iterdir() if p.suffix.lower() in IMAGE_EXTS)


def patch_size_from_model(model, fallback):
    for obj in (getattr(model, "config", None), getattr(getattr(model, "config", None), "vision_config", None)):
        if obj is not None and getattr(obj, "patch_size", None):
            return int(getattr(obj, "patch_size"))
    return int(fallback)


def manual_image_processor(image, args):
    image = image.convert("RGB").resize((args.image_size, args.image_size), Image.BICUBIC)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    mean = np.asarray(args.mean, dtype=np.float32).reshape(1, 1, 3)
    std = np.asarray(args.std, dtype=np.float32).reshape(1, 1, 3)
    arr = (arr - mean) / std
    return {"pixel_values": torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)}


def load_model(args, device):
    from transformers import AutoImageProcessor, AutoModel

    processor = None
    if not args.manual_processor:
        try:
            processor = AutoImageProcessor.from_pretrained(
                args.model,
                local_files_only=args.local_files_only,
                trust_remote_code=True,
            )
        except Exception as exc:
            print(f"Warning: AutoImageProcessor failed, using manual processor: {exc}")

    model = AutoModel.from_pretrained(
        args.model,
        local_files_only=args.local_files_only,
        trust_remote_code=True,
    ).to(device)
    model.eval()
    return model, processor


def extract_one(image_path, model, processor, device, args):
    image = Image.open(image_path).convert("RGB")
    if processor is None or args.manual_processor:
        inputs = manual_image_processor(image, args)
    else:
        inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    tokens = getattr(outputs, "last_hidden_state", None)
    if tokens is None:
        if hasattr(outputs, "hidden_states") and outputs.hidden_states:
            tokens = outputs.hidden_states[-1]
        else:
            raise RuntimeError("Model output has no last_hidden_state.")

    pixel_values = inputs["pixel_values"]
    _, _, proc_h, proc_w = pixel_values.shape
    patch = patch_size_from_model(model, args.patch_size)
    gh = max(1, proc_h // patch)
    gw = max(1, proc_w // patch)
    expected = gh * gw

    if tokens.shape[1] == expected + 1:
        tokens = tokens[:, 1:]
    elif tokens.shape[1] > expected:
        tokens = tokens[:, -expected:]
    elif tokens.shape[1] != expected:
        side = int(round(tokens.shape[1] ** 0.5))
        if side * side != tokens.shape[1]:
            raise RuntimeError(f"Cannot infer patch grid from token count {tokens.shape[1]}.")
        gh = side
        gw = side

    feats = F.normalize(tokens[0].float(), dim=-1).reshape(gh, gw, -1)
    return feats.detach().cpu().numpy(), (gh, gw), (image.height, image.width)


def run(args):
    device = torch.device("cpu" if args.cpu or not torch.cuda.is_available() else "cuda")
    dataset_path = Path(args.dataset_path)
    image_dir = dataset_path / args.image_dir
    out_dir = dataset_path / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = image_paths(image_dir)
    if args.limit > 0:
        paths = paths[: args.limit]
    print(f"Images: {image_dir}")
    print(f"Output: {out_dir}")
    print(f"Model: {args.model}")
    print(f"Device: {device}")

    model, processor = load_model(args, device)
    for i, path in enumerate(paths, 1):
        out_path = out_dir / f"{path.stem}.npz"
        if out_path.exists() and not args.overwrite:
            print(f"[{i}/{len(paths)}] skip {path.name}")
            continue
        feats, grid_hw, image_hw = extract_one(path, model, processor, device, args)
        if args.float16:
            feats = feats.astype(np.float16)
        np.savez_compressed(
            out_path,
            features=feats,
            grid_hw=np.asarray(grid_hw, dtype=np.int32),
            image_hw=np.asarray(image_hw, dtype=np.int32),
        )
        print(f"[{i}/{len(paths)}] saved {out_path.name} {feats.shape}")


def main():
    parser = argparse.ArgumentParser(description="Precompute DINO/DINOv3 patch features for ILGS mask refinement.")
    parser.add_argument("--dataset_path", required=True)
    parser.add_argument("--image_dir", default="images")
    parser.add_argument("--output_dir", default="dino_features/dinov3-vitl16")
    parser.add_argument("--model", required=True)
    parser.add_argument("--local_files_only", action="store_true")
    parser.add_argument("--manual_processor", action="store_true")
    parser.add_argument("--image_size", type=int, default=768)
    parser.add_argument("--patch_size", type=int, default=16)
    parser.add_argument("--mean", nargs=3, type=float, default=[0.485, 0.456, 0.406])
    parser.add_argument("--std", nargs=3, type=float, default=[0.229, 0.224, 0.225])
    parser.add_argument("--float16", action="store_true", default=True)
    parser.add_argument("--float32", dest="float16", action="store_false")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
