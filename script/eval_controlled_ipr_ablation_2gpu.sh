#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin}"
if [ ! -f "$OPENCLIP_CHECKPOINT" ]; then
  echo "Missing local OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2
  exit 1
fi

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_controlled_ablation}"
SEEDS="${SEEDS:-0 1 2}"
SCENES="${SCENES:-figurines ramen teatime}"
VARIANTS="${VARIANTS:-official cleanup cleanup_conf no_semantic no_visibility semantic_only large_only no_large full}"

mkdir -p "$EXTERNAL_ROOT"
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"
mkdir -p "$EXTERNAL_ROOT/logs/eval"

run_task() {
  local task="$1"
  local gpu="$2"
  local scene variant seed
  IFS='|' read -r scene variant seed <<< "$task"

  local name="${scene}_ipr_${variant}_s${seed}"
  local model="output/lerf/$name"
  local log="$EXTERNAL_ROOT/logs/eval/eval_${name}.txt"
  local gt="dataset/lerf/$scene/test_mask"

  [ -f "$model/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -f "$model/point_cloud/iteration_30000/classifier.pth" ] || {
    echo "Missing completed model: $model" >&2
    return 1
  }
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
    --mode official \
    --clip_checkpoint "$OPENCLIP_CHECKPOINT"

  python script/eval_lerf_mask.py \
    -m "$model" \
    --gt_path "$gt" 2>&1 | tee "$log"
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

worker 0 0 &
pid0=$!
worker 1 1 &
pid1=$!
status=0
if ! wait "$pid0"; then status=1; fi
if ! wait "$pid1"; then status=1; fi
if [ "$status" -ne 0 ]; then
  echo "At least one evaluation worker failed. Inspect $EXTERNAL_ROOT/logs/eval." >&2
  exit "$status"
fi

python script/summarize_controlled_ipr_ablation.py \
  --log_dir "$EXTERNAL_ROOT/logs/eval" \
  --output_dir "$EXTERNAL_ROOT/reports"
