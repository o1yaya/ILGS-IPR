#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SAM_CHECKPOINT="${SAM_CHECKPOINT:-ckpts/sam_vit_h_4b8939.pth}"
SCENES="${SCENES:-bed}"
GPU="${GPU:-0}"
IMAGE_DIR="${IMAGE_DIR:-images_4}"

for path in "$OPENCLIP_CHECKPOINT" "$SAM_CHECKPOINT"; do
  [ -f "$path" ] || { echo "Missing checkpoint: $path" >&2; exit 1; }
done

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  [ -d "$dataset/images" ] || { echo "Missing $dataset/images" >&2; exit 1; }
  dataset_abs="$(cd "$dataset" && pwd)"

  if [ ! -d "$dataset/$IMAGE_DIR" ]; then
    echo "[$scene] Preparing quarter-resolution images..."
    python script/prepare_deva_resized_images.py \
      --src "$dataset/images" \
      --dst "$dataset/$IMAGE_DIR" \
      --scale 4
  fi

  if ! compgen -G "$dataset/language_features/*_f.npy" > /dev/null; then
    echo "[$scene] Extracting SAM + OpenCLIP language features..."
    CUDA_VISIBLE_DEVICES="$GPU" python preprocess.py \
      --dataset_path "$dataset" \
      --image_dir "$IMAGE_DIR" \
      --sam_ckpt_path "$SAM_CHECKPOINT" \
      --clip_checkpoint "$OPENCLIP_CHECKPOINT"
  else
    echo "[$scene] Skip existing language_features"
  fi

  if [ ! -f "autoencoder/ckpt/3dovs/$scene/best_ckpt.pth" ]; then
    echo "[$scene] Training language-feature autoencoder..."
    (
      cd autoencoder
      CUDA_VISIBLE_DEVICES="$GPU" python train.py \
        --dataset_path "$dataset_abs" \
        --dataset_name "3dovs/$scene"
    )
  else
    echo "[$scene] Skip existing autoencoder checkpoint"
  fi

  if ! compgen -G "$dataset/language_features_dim3/*_f.npy" > /dev/null; then
    echo "[$scene] Encoding 3D language features..."
    (
      cd autoencoder
      CUDA_VISIBLE_DEVICES="$GPU" python test.py \
        --dataset_path "$dataset_abs" \
        --dataset_name "3dovs/$scene"
    )
  else
    echo "[$scene] Skip existing language_features_dim3"
  fi
done

echo "3D-OVS language features are ready."
