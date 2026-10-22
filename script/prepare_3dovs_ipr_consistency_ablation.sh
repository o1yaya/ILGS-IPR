#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-bench snacks covered_desk}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"

[ -f "$OPENCLIP_CHECKPOINT" ] || {
  echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
}

# Rebuild the shared train-view-only masks, base confidence, and full IPR map so
# every ablation starts from exactly the same preprocessing state.
DATASET_ROOT="$DATASET_ROOT" \
OPENCLIP_CHECKPOINT="$OPENCLIP_CHECKPOINT" \
SCENES="$SCENES" \
CONSISTENCY_THRESHOLD="$CONSISTENCY_THRESHOLD" \
bash script/prepare_3dovs_ipr_consistency.sh

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"

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

  echo "[$scene] Strict consistency ablation inputs are ready."
done

echo "All requested 3D-OVS strict-consistency ablation inputs are ready."
