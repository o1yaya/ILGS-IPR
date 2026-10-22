#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
SCENES="${SCENES:-figurines ramen teatime}"
INDEPENDENT_VOCAB="${INDEPENDENT_VOCAB:-config/ipr_vocab/scene_independent_v1.txt}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"

[ -f "$OPENCLIP_CHECKPOINT" ] || { echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2; exit 1; }
[ -f "$INDEPENDENT_VOCAB" ] || { echo "Missing independent vocabulary: $INDEPENDENT_VOCAB" >&2; exit 1; }

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  protocol_dir="$dataset/ipr_protocol"
  eval_queries="$protocol_dir/evaluation_queries.txt"
  mkdir -p "$protocol_dir"

  echo "[$scene] Building evaluation-query audit file..."
  python script/build_query_file_from_masks.py \
    --gt_path "$dataset/test_mask" \
    --output "$eval_queries"

  python script/audit_ipr_vocabulary.py \
    --preprocess_vocab "$INDEPENDENT_VOCAB" \
    --eval_queries "$eval_queries" \
    --output "$protocol_dir/independent_vocabulary_audit.json" \
    --require_zero_exact \
    --require_zero_phrase_overlap

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

  echo "[$scene] Train-view-only IPR using evaluation vocabulary (view control)..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --query_file "$eval_queries" \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --conf_dst object_confidence_ipr_trainview_evalvocab_strict \
    --report_dir object_mask_ipr_trainview_evalvocab_strict_report \
    --disable_visibility_weight \
    --confidence_only

  echo "[$scene] Train-view-only IPR using scene-independent vocabulary..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --query_file "$INDEPENDENT_VOCAB" \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --conf_dst object_confidence_ipr_trainview_independent_strict \
    --report_dir object_mask_ipr_trainview_independent_strict_report \
    --disable_visibility_weight \
    --confidence_only

  echo "[$scene] Train-view-only query-free area prior..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --dataset_name "$scene" \
    --src object_mask_refined_trainonly_strict \
    --conf_src object_confidence_refined_trainonly_strict \
    --image_dir images \
    --conf_dst object_confidence_ipr_trainview_areaonly_strict \
    --report_dir object_mask_ipr_trainview_areaonly_strict_report \
    --area_only \
    --disable_visibility_weight \
    --confidence_only

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
