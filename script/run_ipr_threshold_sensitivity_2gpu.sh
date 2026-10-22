#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

ROOT="${ROOT:-/media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity}"
LERF_ROOT="${LERF_ROOT:-$ROOT/lerf_mask}"
OVS_ROOT="${OVS_ROOT:-$ROOT/3dovs}"
LERF_DATASET_ROOT="${LERF_DATASET_ROOT:-dataset/lerf}"
OVS_DATASET_ROOT="${OVS_DATASET_ROOT:-dataset/3dovs}"
LERF_SCENES="${LERF_SCENES:-ramen figurines teatime}"
OVS_SCENES="${OVS_SCENES:-bench covered_desk snacks}"
THRESHOLDS="${THRESHOLDS:-0.65 0.70 0.75 0.80 0.85}"
SEED="${SEED:-0}"
STAGES="${STAGES:-prepare train eval summarize}"

has_stage() {
  case " $STAGES " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

threshold_code() {
  local value="$1"
  [[ "$value" =~ ^0\.[0-9][0-9]$ ]] || {
    echo "Threshold must use two decimals: $value" >&2
    return 1
  }
  printf '%s' "${value/./}"
}

variants=""
for threshold in $THRESHOLDS; do
  code="$(threshold_code "$threshold")"
  variants+=" strict_trainview_consistency_t${code}"
done
variants="${variants# }"

mkdir -p "$LERF_ROOT/reports" "$OVS_ROOT/reports"

if has_stage prepare; then
  DATASET_ROOT="$LERF_DATASET_ROOT" \
  SCENES="$LERF_SCENES" \
  THRESHOLDS="$THRESHOLDS" \
  bash script/prepare_ipr_threshold_sensitivity.sh

  DATASET_ROOT="$OVS_DATASET_ROOT" \
  SCENES="$OVS_SCENES" \
  THRESHOLDS="$THRESHOLDS" \
  bash script/prepare_ipr_threshold_sensitivity.sh
fi

if has_stage train; then
  EXTERNAL_ROOT="$LERF_ROOT" \
  DATASET_ROOT="$LERF_DATASET_ROOT" \
  SCENES="$LERF_SCENES" \
  VARIANTS="$variants" \
  SEEDS="$SEED" \
  RESOLUTION=1 \
  bash script/run_ipr_strict_protocol_2gpu.sh

  EXTERNAL_ROOT="$OVS_ROOT" \
  DATASET_ROOT="$OVS_DATASET_ROOT" \
  SCENES="$OVS_SCENES" \
  VARIANTS="$variants" \
  SEEDS="$SEED" \
  RESOLUTION=4 \
  bash script/run_3dovs_controlled_2gpu.sh
fi

if has_stage eval; then
  EXTERNAL_ROOT="$LERF_ROOT" \
  DATASET_ROOT="$LERF_DATASET_ROOT" \
  SCENES="$LERF_SCENES" \
  VARIANTS="$variants" \
  SEEDS="$SEED" \
  MASK_MODE=official \
  bash script/eval_ipr_strict_protocol_2gpu.sh

  EXTERNAL_ROOT="$OVS_ROOT" \
  REPORT_DIR="$OVS_ROOT/reports" \
  DATASET_ROOT="$OVS_DATASET_ROOT" \
  SCENES="$OVS_SCENES" \
  VARIANTS="$variants" \
  SEEDS="$SEED" \
  bash script/eval_3dovs_controlled_2gpu.sh
fi

if has_stage summarize; then
  python script/summarize_ipr_threshold_sensitivity.py \
    --dataset_root "$LERF_DATASET_ROOT" \
    --log_dir "$LERF_ROOT/logs/eval" \
    --output_dir "$LERF_ROOT/reports/threshold_sensitivity" \
    --scenes $LERF_SCENES \
    --thresholds $THRESHOLDS \
    --seed "$SEED" \
    --title "LERF-Mask IPR threshold sensitivity"

  python script/summarize_ipr_threshold_sensitivity.py \
    --dataset_root "$OVS_DATASET_ROOT" \
    --log_dir "$OVS_ROOT/logs/eval" \
    --output_dir "$OVS_ROOT/reports/threshold_sensitivity" \
    --scenes $OVS_SCENES \
    --thresholds $THRESHOLDS \
    --seed "$SEED" \
    --title "3D-OVS IPR threshold sensitivity"
fi

echo "Threshold sensitivity experiment complete."
echo "LERF report: $LERF_ROOT/reports/threshold_sensitivity/threshold_sensitivity_summary.md"
echo "3D-OVS report: $OVS_ROOT/reports/threshold_sensitivity/threshold_sensitivity_summary.md"
