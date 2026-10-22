#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-checkpoints/open_clip_pytorch_model.bin}"
EXTERNAL_ROOT="${EXTERNAL_ROOT:-results/lerf_mask/main}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
AUTOENCODER_ROOT="${AUTOENCODER_ROOT:-autoencoder/ckpt/lerf}"
SCENES="${SCENES:-figurines ramen teatime}"
SEEDS="${SEEDS:-0 1 2}"
VARIANTS="${VARIANTS:-official strict_trainview_consistency}"
MASK_MODE="${MASK_MODE:-official}"

[ -f "$OPENCLIP_CHECKPOINT" ] || { echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2; exit 1; }
mkdir -p "$EXTERNAL_ROOT/logs/eval" "$EXTERNAL_ROOT/reports"

run_task() {
  local task="$1"
  local gpu="$2"
  local scene variant seed
  IFS='|' read -r scene variant seed <<< "$task"
  local name="${scene}_ipr_${variant}_s${seed}"
  local model="output/lerf/$name"
  local dataset="$DATASET_ROOT/$scene"
  local gt="$dataset/test_mask"
  local query_file="$dataset/ipr_protocol/evaluation_queries.txt"
  local ae="$AUTOENCODER_ROOT/$scene/best_ckpt.pth"
  local pred="$model/test/ours_30000_text/test_mask_${MASK_MODE}_${variant}"
  local log="$EXTERNAL_ROOT/logs/eval/eval_${name}.txt"

  [ -s "$model/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -s "$model/point_cloud/iteration_30000/classifier.pth" ] || {
      echo "Missing completed model: $model" >&2; return 1;
    }
  [ -f "$query_file" ] || { echo "Missing query file: $query_file" >&2; return 1; }
  [ -f "$ae" ] || { echo "Missing autoencoder checkpoint: $ae" >&2; return 1; }
  if grep -q "Overall Boundary Mean IoU:" "$log" 2>/dev/null; then
    echo "[GPU $gpu] Skip evaluated: $name"
    return 0
  fi

  echo "[GPU $gpu] Rendering and evaluating $name"
  CUDA_VISIBLE_DEVICES="$gpu" python render_all.py \
    -s "$dataset" -m "$model" --skip_train --train_split
  CUDA_VISIBLE_DEVICES="$gpu" python segmentation_mask_stream.py \
    -m "$model" \
    --dataset_name "$scene" \
    --query_file "$query_file" \
    --autoencoder_checkpoint "$ae" \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
    --mode "$MASK_MODE" \
    --output_dir "$pred"
  python script/eval_lerf_mask.py \
    -m "$model" --gt_path "$gt" --pred_path "$pred" 2>&1 | tee "$log"
}

TASKS=()
for scene in $SCENES; do
  for variant in $VARIANTS; do
    for seed in $SEEDS; do
      TASKS+=("$scene|$variant|$seed")
    done
  done
done

worker() {
  local gpu="$1"
  local start="$2"
  local i
  for ((i=start; i<${#TASKS[@]}; i+=2)); do
    run_task "${TASKS[$i]}" "$gpu"
  done
}

worker 0 0 & pid0=$!
worker 1 1 & pid1=$!
status=0
if ! wait "$pid0"; then status=1; fi
if ! wait "$pid1"; then status=1; fi
[ "$status" -eq 0 ] || { echo "At least one strict-protocol evaluation worker failed." >&2; exit "$status"; }

python script/summarize_controlled_ipr_ablation.py \
  --log_dir "$EXTERNAL_ROOT/logs/eval" \
  --output_dir "$EXTERNAL_ROOT/reports" \
  --scenes $SCENES \
  --variants $VARIANTS \
  --title "IPR strict protocol controls"

echo "Report: $EXTERNAL_ROOT/reports/controlled_ablation_summary.md"
