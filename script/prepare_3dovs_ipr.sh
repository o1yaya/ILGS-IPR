#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-bed}"

[ -f "$OPENCLIP_CHECKPOINT" ] || {
  echo "Missing local OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
}

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  raw="$dataset/object_mask_deva_raw"
  [ -d "$raw" ] || {
    echo "Missing DEVA RGB masks: $raw" >&2
    echo "Run script/run_deva_object_masks.sh 3dovs/$scene 1 <DEVA_ROOT> object_mask_deva_raw first." >&2
    exit 1
  }

  echo "[$scene] Converting DEVA RGB tracks to identity labels..."
  python script/convert_deva_rgb_to_labels.py \
    --src "$raw" \
    --dst "$dataset/object_mask" \
    --image_dir "$dataset/images"

  echo "[$scene] Cleaning identity masks and building base confidence..."
  python refine_object_masks.py \
    --dataset_path "$dataset" \
    --src object_mask \
    --dst object_mask_refined \
    --conf_dst object_confidence_refined \
    --report_dir object_mask_refine_report

  echo "[$scene] Computing final IPR confidence (semantic + large-region, no visibility)..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined \
    --conf_src object_confidence_refined \
    --query_file "$dataset/queries.txt" \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --conf_dst object_confidence_ipr \
    --report_dir object_mask_ipr_report \
    --disable_visibility_weight \
    --confidence_only
done

echo "3D-OVS identity masks and final IPR confidence maps are ready."
