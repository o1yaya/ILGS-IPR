#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

if [ "$#" -gt 0 ]; then
  SCENES=("$@")
else
  SCENES=(figurines ramen teatime)
fi

for scene in "${SCENES[@]}"; do
  dataset="dataset/lerf/$scene"
  semantic_json="$dataset/object_mask_ipr_controlled_full_report/object_semantics.json"

  if [ ! -d "$dataset/object_mask_refined" ] \
    || [ ! -d "$dataset/object_confidence_refined" ]; then
    echo "Missing refined masks/confidence for $scene" >&2
    exit 1
  fi
  if [ ! -f "$semantic_json" ]; then
    echo "Missing cached semantic report: $semantic_json" >&2
    exit 1
  fi

  echo "[$scene] Preparing large-region-only confidence maps..."
  python refine_object_masks_semantic_area.py \
    --dataset_path "$dataset" \
    --src object_mask_refined \
    --conf_src object_confidence_refined \
    --semantic_json object_mask_ipr_controlled_full_report/object_semantics.json \
    --conf_dst object_confidence_ipr_large_only \
    --report_dir object_mask_ipr_large_only_report \
    --disable_semantic_weight \
    --disable_visibility_weight \
    --confidence_only
done

echo "Large-region-only confidence maps are ready."
