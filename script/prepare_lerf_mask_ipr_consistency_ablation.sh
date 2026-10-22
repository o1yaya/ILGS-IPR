#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-checkpoints/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-ramen figurines teatime}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"

[ -f "$OPENCLIP_CHECKPOINT" ] || {
  echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
}

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  [ -d "$dataset/images_train" ] || { echo "Missing $dataset/images_train" >&2; exit 1; }
  [ -d "$dataset/object_mask" ] || { echo "Missing $dataset/object_mask" >&2; exit 1; }

  echo "[$scene] Materializing raw train-view-only masks..."
  python script/subset_ipr_training_views.py \
    --dataset_path "$dataset" \
    --image_train_dir images_train \
    --mask_src object_mask \
    --mask_dst object_mask_trainonly_raw_strict \
    --mask_only

  echo "[$scene] Rebuilding the shared cleanup and base confidence..."
  python refine_object_masks.py \
    --dataset_path "$dataset" \
    --src object_mask_trainonly_raw_strict \
    --dst object_mask_refined_trainonly_strict \
    --conf_dst object_confidence_refined_trainonly_strict \
    --report_dir object_mask_refine_trainonly_strict_report

  echo "[$scene] Preparing consistency-only confidence maps..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --clip_consistency \
    --consistency_threshold "$CONSISTENCY_THRESHOLD" \
    --conf_dst object_confidence_ipr_trainview_consistency_only_strict \
    --report_dir object_mask_ipr_trainview_consistency_only_strict_report \
    --disable_visibility_weight \
    --disable_large_region_weight \
    --confidence_only

  echo "[$scene] Preparing large-region-only confidence maps..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --area_only \
    --conf_dst object_confidence_ipr_trainview_large_only_strict \
    --report_dir object_mask_ipr_trainview_large_only_strict_report \
    --disable_visibility_weight \
    --confidence_only

  echo "[$scene] Rebuilding the full query-free IPR map at threshold $CONSISTENCY_THRESHOLD..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --clip_consistency \
    --consistency_threshold "$CONSISTENCY_THRESHOLD" \
    --conf_dst object_confidence_ipr_trainview_consistency_strict \
    --report_dir object_mask_ipr_trainview_consistency_strict_report \
    --disable_visibility_weight \
    --confidence_only
done

echo "All requested LERF-Mask strict-consistency ablation inputs are ready."
