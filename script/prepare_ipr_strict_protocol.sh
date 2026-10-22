#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-checkpoints/open_clip_pytorch_model.bin}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
SCENES="${SCENES:-figurines ramen teatime}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"

[ -f "$OPENCLIP_CHECKPOINT" ] || { echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2; exit 1; }

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  protocol_dir="$dataset/ipr_protocol"
  eval_queries="$protocol_dir/evaluation_queries.txt"
  mkdir -p "$protocol_dir"

  echo "[$scene] Building evaluation-query audit file..."
  python script/build_query_file_from_masks.py \
    --gt_path "$dataset/test_mask" \
    --output "$eval_queries"

  echo "[$scene] Materializing raw train-view-only masks..."
  python script/subset_ipr_training_views.py \
    --dataset_path "$dataset" \
    --mask_src object_mask \
    --mask_dst object_mask_trainonly_raw \
    --mask_only

  echo "[$scene] Cleaning masks using train-view statistics only..."
  python refine_object_masks.py \
    --dataset_path "$dataset" \
    --src object_mask_trainonly_raw \
    --dst object_mask_refined_trainonly_strict \
    --conf_dst object_confidence_refined_trainonly_strict \
    --report_dir object_mask_refine_trainonly_strict_report

  echo "[$scene] Train-view-only query-free CLIP consistency..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --conf_dst object_confidence_ipr_trainview_consistency_strict \
    --report_dir object_mask_ipr_trainview_consistency_strict_report \
    --clip_consistency \
    --consistency_threshold "$CONSISTENCY_THRESHOLD" \
    --disable_visibility_weight \
    --confidence_only
done

echo "Strict-protocol IPR inputs are ready."
