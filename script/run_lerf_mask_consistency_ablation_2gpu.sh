#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_lerf_mask_consistency_ablation}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-ramen figurines teatime}"
SEEDS="${SEEDS:-0}"
RESOLUTION="${RESOLUTION:-1}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"
VARIANTS="${VARIANTS:-official strict_trainview_cleanup strict_trainview_cleanup_conf strict_trainview_consistency_only strict_trainview_large_only strict_trainview_consistency}"

mkdir -p "$EXTERNAL_ROOT/logs" "$EXTERNAL_ROOT/reports"
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"

echo "Current reusable endpoints before preprocessing:"
for scene in $SCENES; do
  for variant in official strict_trainview_consistency; do
    model="output/lerf/${scene}_ipr_${variant}_s0"
    if [ -e "$model" ]; then
      echo "  $scene $variant -> $(readlink -f "$model")"
    else
      echo "  $scene $variant -> MISSING"
    fi
  done
done

DATASET_ROOT="$DATASET_ROOT" \
OPENCLIP_CHECKPOINT="$OPENCLIP_CHECKPOINT" \
SCENES="$SCENES" \
CONSISTENCY_THRESHOLD="$CONSISTENCY_THRESHOLD" \
bash script/prepare_lerf_mask_ipr_consistency_ablation.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/prepare_ablation.txt"

python script/audit_3dovs_ipr_consistency_ablation.py \
  --dataset_root "$DATASET_ROOT" \
  --scenes $SCENES \
  --output "$EXTERNAL_ROOT/reports/input_ablation_audit.json" \
  2>&1 | tee "$EXTERNAL_ROOT/logs/audit_ablation.txt"

EXTERNAL_ROOT="$EXTERNAL_ROOT" \
DATASET_ROOT="$DATASET_ROOT" \
SCENES="$SCENES" \
VARIANTS="$VARIANTS" \
SEEDS="$SEEDS" \
RESOLUTION="$RESOLUTION" \
REUSE_CURRENT_MODELS=1 \
bash script/run_ipr_strict_protocol_2gpu.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/train_ablation_launcher.txt"

EXTERNAL_ROOT="$EXTERNAL_ROOT" \
DATASET_ROOT="$DATASET_ROOT" \
OPENCLIP_CHECKPOINT="$OPENCLIP_CHECKPOINT" \
SCENES="$SCENES" \
VARIANTS="$VARIANTS" \
SEEDS="$SEEDS" \
MASK_MODE=official \
bash script/eval_ipr_strict_protocol_2gpu.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/eval_ablation_launcher.txt"

echo "LERF-Mask ablation report: $EXTERNAL_ROOT/reports/controlled_ablation_summary.md"
