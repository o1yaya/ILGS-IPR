#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_3dovs_consistency_t075_pilot}"
DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
SCENES="${SCENES:-bench covered_desk}"
SEEDS="${SEEDS:-0}"
RESOLUTION="${RESOLUTION:-4}"
CONSISTENCY_THRESHOLD="${CONSISTENCY_THRESHOLD:-0.75}"

mkdir -p "$ROOT/logs/prepare" "$ROOT/logs/train" "$ROOT/logs/eval" "$ROOT/reports"

for scene in $SCENES; do
  model="output/3dovs/${scene}_ipr_official_s0/point_cloud/iteration_30000"
  [ -s "$model/point_cloud.ply" ] && [ -s "$model/classifier.pth" ] || {
    echo "Missing official seed-0 model for $scene: $model" >&2
    exit 1
  }
done

pids=()
gpu=0
for scene in $SCENES; do
  echo "[prepare] $scene on GPU $gpu"
  CUDA_VISIBLE_DEVICES="$gpu" \
  DATASET_ROOT="$DATASET_ROOT" \
  SCENES="$scene" \
  CONSISTENCY_THRESHOLD="$CONSISTENCY_THRESHOLD" \
  bash script/prepare_3dovs_ipr_consistency.sh \
    > "$ROOT/logs/prepare/${scene}.txt" 2>&1 &
  pids+=("$!")
  gpu=$((1 - gpu))
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then status=1; fi
done
[ "$status" -eq 0 ] || {
  echo "At least one preprocessing worker failed. Inspect $ROOT/logs/prepare." >&2
  exit "$status"
}

echo "[train] strict train-view consistency IPR"
EXTERNAL_ROOT="$ROOT" \
DATASET_ROOT="$DATASET_ROOT" \
SCENES="$SCENES" \
VARIANTS="strict_trainview_consistency" \
SEEDS="$SEEDS" \
RESOLUTION="$RESOLUTION" \
bash script/run_3dovs_controlled_2gpu.sh

echo "[eval] official versus strict train-view consistency IPR"
EXTERNAL_ROOT="$ROOT" \
REPORT_DIR="$ROOT/reports" \
DATASET_ROOT="$DATASET_ROOT" \
SCENES="$SCENES" \
VARIANTS="official strict_trainview_consistency" \
SEEDS="$SEEDS" \
bash script/eval_3dovs_controlled_2gpu.sh

echo "[done] $ROOT/reports/controlled_ablation_summary.md"
