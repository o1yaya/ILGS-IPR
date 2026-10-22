#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
SCENES="${SCENES:-ramen figurines teatime}"
THRESHOLDS="${THRESHOLDS:-0.65 0.70 0.75 0.80 0.85}"

threshold_code() {
  local value="$1"
  [[ "$value" =~ ^0\.[0-9][0-9]$ ]] || {
    echo "Threshold must use two decimals in [0, 1), for example 0.75: $value" >&2
    return 1
  }
  printf '%s' "${value/./}"
}

for scene in $SCENES; do
  dataset="$DATASET_ROOT/$scene"
  semantic_json="object_mask_ipr_trainview_consistency_strict_report/object_semantics.json"

  [ -d "$dataset/object_mask_refined_trainonly_strict" ] || {
    echo "Missing cleaned train-view masks: $dataset/object_mask_refined_trainonly_strict" >&2
    exit 1
  }
  [ -d "$dataset/object_confidence_refined_trainonly_strict" ] || {
    echo "Missing base confidence maps: $dataset/object_confidence_refined_trainonly_strict" >&2
    exit 1
  }
  [ -f "$dataset/$semantic_json" ] || {
    echo "Missing cached consistency scores: $dataset/$semantic_json" >&2
    echo "Run the standard strict-consistency preprocessing once before the sweep." >&2
    exit 1
  }

  for threshold in $THRESHOLDS; do
    code="$(threshold_code "$threshold")"
    conf_dst="object_confidence_ipr_trainview_consistency_t${code}"
    report_dir="object_mask_ipr_trainview_consistency_t${code}_report"

    echo "[$scene] Reweighting cached consistency scores at threshold=$threshold..."
    python refine_object_masks_semantic_area.py \
      --dataset_path "$dataset" \
      --dataset_name "$scene" \
      --src object_mask_refined_trainonly_strict \
      --conf_src object_confidence_refined_trainonly_strict \
      --image_dir images \
      --semantic_json "$semantic_json" \
      --semantic_conf_threshold "$threshold" \
      --consistency_threshold "$threshold" \
      --conf_dst "$conf_dst" \
      --report_dir "$report_dir" \
      --disable_visibility_weight \
      --confidence_only
  done
done

echo "Threshold-specific confidence maps are ready."
