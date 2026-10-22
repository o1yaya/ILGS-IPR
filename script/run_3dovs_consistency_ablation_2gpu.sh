#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_3dovs_consistency_ablation}"
REUSE_ROOT="${REUSE_ROOT:-}"
DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-bench snacks covered_desk}"
SEEDS="${SEEDS:-0}"
RESOLUTION="${RESOLUTION:-4}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"
VARIANTS="${VARIANTS:-official strict_trainview_cleanup strict_trainview_cleanup_conf strict_trainview_consistency_only strict_trainview_large_only strict_trainview_consistency}"

mkdir -p "$EXTERNAL_ROOT/logs" "$EXTERNAL_ROOT/reports"
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"

if [ -z "$REUSE_ROOT" ]; then
  first_scene="${SCENES%% *}"
  anchor="output/3dovs/${first_scene}_ipr_strict_trainview_consistency_s0"
  if [ -e "$anchor" ]; then
    resolved_anchor="$(readlink -f "$anchor")"
    case "$resolved_anchor" in
      */output/3dovs/*)
        REUSE_ROOT="${resolved_anchor%%/output/3dovs/*}"
        echo "Auto-detected reusable main-result root: $REUSE_ROOT"
        ;;
    esac
  fi
fi

echo "Preparing strict, query-free ablation inputs..."
DATASET_ROOT="$DATASET_ROOT" \
OPENCLIP_CHECKPOINT="$OPENCLIP_CHECKPOINT" \
SCENES="$SCENES" \
CONSISTENCY_THRESHOLD="$CONSISTENCY_THRESHOLD" \
bash script/prepare_3dovs_ipr_consistency_ablation.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/prepare_ablation.txt"

python script/audit_3dovs_ipr_consistency_ablation.py \
  --dataset_root "$DATASET_ROOT" \
  --scenes $SCENES \
  --output "$EXTERNAL_ROOT/reports/input_ablation_audit.json" \
  2>&1 | tee "$EXTERNAL_ROOT/logs/audit_ablation.txt"

echo "Training strict, query-free component variants..."
EXTERNAL_ROOT="$EXTERNAL_ROOT" \
REUSE_ROOT="$REUSE_ROOT" \
DATASET_ROOT="$DATASET_ROOT" \
SCENES="$SCENES" \
VARIANTS="$VARIANTS" \
SEEDS="$SEEDS" \
RESOLUTION="$RESOLUTION" \
bash script/run_3dovs_controlled_2gpu.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/train_ablation_launcher.txt"

echo "Evaluating strict, query-free component variants..."
EXTERNAL_ROOT="$EXTERNAL_ROOT" \
REPORT_DIR="$EXTERNAL_ROOT/reports" \
DATASET_ROOT="$DATASET_ROOT" \
OPENCLIP_CHECKPOINT="$OPENCLIP_CHECKPOINT" \
SCENES="$SCENES" \
VARIANTS="$VARIANTS" \
SEEDS="$SEEDS" \
bash script/eval_3dovs_controlled_2gpu.sh \
  2>&1 | tee "$EXTERNAL_ROOT/logs/eval_ablation_launcher.txt"

echo "Ablation report: $EXTERNAL_ROOT/reports/controlled_ablation_summary.md"
