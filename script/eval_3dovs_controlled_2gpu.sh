#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_3dovs}"
REPORT_DIR="${REPORT_DIR:-$EXTERNAL_ROOT/reports}"
DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
SCENES="${SCENES:-bed}"
VARIANTS="${VARIANTS:-official ipr}"
SEEDS="${SEEDS:-0}"

[ -f "$OPENCLIP_CHECKPOINT" ] || {
  echo "Missing local OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
}
mkdir -p "$EXTERNAL_ROOT/logs/eval" "$REPORT_DIR"

run_task() {
  local task="$1" gpu="$2"
  local scene variant seed
  IFS='|' read -r scene variant seed <<< "$task"
  local name="${scene}_ipr_${variant}_s${seed}"
  local model="output/3dovs/$name"
  local dataset="$DATASET_ROOT/$scene"
  local log="$EXTERNAL_ROOT/logs/eval/eval_${name}.txt"
  local ae="autoencoder/ckpt/3dovs/$scene/best_ckpt.pth"

  [ -f "$model/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -f "$model/point_cloud/iteration_30000/classifier.pth" ] || {
    echo "Missing completed model: $model" >&2
    return 1
  }
  [ -f "$ae" ] || { echo "Missing autoencoder: $ae" >&2; return 1; }
  if grep -q "Overall Boundary Mean IoU:" "$log" 2>/dev/null; then
    echo "[GPU $gpu] Skip evaluated: $name"
    return 0
  fi

  echo "[GPU $gpu] Rendering and evaluating $name"
  CUDA_VISIBLE_DEVICES="$gpu" python render_all.py \
    -m "$model" \
    --skip_train \
    --train_split

  rm -rf "$model/test/ours_30000_text/test_mask"
  CUDA_VISIBLE_DEVICES="$gpu" python segmentation_mask_stream.py \
    -m "$model" \
    --dataset_name "3dovs/$scene" \
    --query_file "$dataset/queries.txt" \
    --autoencoder_checkpoint "$ae" \
    --mode seed_ref \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT"

  python script/eval_lerf_mask.py \
    -m "$model" \
    --gt_path "$dataset/test_mask" 2>&1 | tee "$log"
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
  local gpu="$1" start="$2" i
  for ((i=start; i<${#TASKS[@]}; i+=2)); do
    run_task "${TASKS[$i]}" "$gpu"
  done
}

worker 0 0 & pid0=$!
worker 1 1 & pid1=$!
status=0
if ! wait "$pid0"; then status=1; fi
if ! wait "$pid1"; then status=1; fi
[ "$status" -eq 0 ] || {
  echo "At least one 3D-OVS evaluation worker failed. Inspect $EXTERNAL_ROOT/logs/eval." >&2
  exit "$status"
}

python script/summarize_controlled_ipr_ablation.py \
  --log_dir "$EXTERNAL_ROOT/logs/eval" \
  --output_dir "$REPORT_DIR" \
  --scenes $SCENES \
  --variants $VARIANTS \
  --title "3D-OVS controlled IPR comparison"

echo "Report: $REPORT_DIR/controlled_ablation_summary.md"
