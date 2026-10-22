#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
if [ ! -f "$OPENCLIP_CHECKPOINT" ]; then
  echo "Missing local OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  SCENES=("$@")
else
  SCENES=(figurines ramen teatime)
fi

for scene in "${SCENES[@]}"; do
    dataset="dataset/lerf/$scene"
    if [ ! -d "$dataset/object_mask_refined" ] || [ ! -d "$dataset/object_confidence_refined" ]; then
      echo "Missing refined masks/confidence for $scene. Run refine_object_masks.py first." >&2
      exit 1
    fi

    echo "[$scene] Computing shared CLIP object semantics and full IPR confidence..."
    python refine_object_masks_semantic_area.py \
      --dataset_path "$dataset" \
      --src object_mask_refined \
      --conf_src object_confidence_refined \
      --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
      --conf_dst object_confidence_ipr_controlled_full \
      --report_dir object_mask_ipr_controlled_full_report \
      --confidence_only

    semantic_json="object_mask_ipr_controlled_full_report/object_semantics.json"

    echo "[$scene] Ablating semantic confidence..."
    python refine_object_masks_semantic_area.py \
      --dataset_path "$dataset" \
      --src object_mask_refined \
      --conf_src object_confidence_refined \
      --semantic_json "$semantic_json" \
      --conf_dst object_confidence_ipr_no_semantic \
      --report_dir object_mask_ipr_no_semantic_report \
      --disable_semantic_weight \
      --confidence_only

    echo "[$scene] Ablating visibility/area consistency..."
    python refine_object_masks_semantic_area.py \
      --dataset_path "$dataset" \
      --src object_mask_refined \
      --conf_src object_confidence_refined \
      --semantic_json "$semantic_json" \
      --conf_dst object_confidence_ipr_no_visibility \
      --report_dir object_mask_ipr_no_visibility_report \
      --disable_visibility_weight \
      --confidence_only

    echo "[$scene] Ablating large mixed-region suppression..."
    python refine_object_masks_semantic_area.py \
      --dataset_path "$dataset" \
      --src object_mask_refined \
      --conf_src object_confidence_refined \
      --semantic_json "$semantic_json" \
      --conf_dst object_confidence_ipr_no_large \
      --report_dir object_mask_ipr_no_large_report \
      --disable_large_region_weight \
      --confidence_only
done

echo "Controlled IPR confidence maps are ready. Object IDs remain in object_mask_refined."
