#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_controlled_ablation}"
SEEDS="${SEEDS:-0 1 2}"
SCENES="${SCENES:-figurines ramen teatime}"
VARIANTS="${VARIANTS:-official cleanup cleanup_conf no_semantic no_visibility semantic_only large_only no_large full}"

mkdir -p "$EXTERNAL_ROOT"
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"
mkdir -p "$EXTERNAL_ROOT/output/lerf" "$EXTERNAL_ROOT/logs/train" output/lerf

variant_inputs() {
  case "$1" in
    official)      MASK_DIR="object_mask";         CONF_DIR="" ;;
    cleanup)       MASK_DIR="object_mask_refined"; CONF_DIR="" ;;
    cleanup_conf)  MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_refined" ;;
    no_semantic)   MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_no_semantic" ;;
    no_visibility) MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_no_visibility" ;;
    semantic_only) MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_semantic_only" ;;
    large_only)    MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_large_only" ;;
    no_large)      MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_no_large" ;;
    full)          MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr_controlled_full" ;;
    *) echo "Unknown variant: $1" >&2; return 1 ;;
  esac
}

ensure_model_link() {
  local target="$1"
  local link="$2"
  mkdir -p "$target"
  if [ -L "$link" ]; then
    ln -sfn "$target" "$link"
  elif [ -e "$link" ]; then
    echo "Refusing to replace existing non-symlink path: $link" >&2
    return 1
  else
    ln -s "$target" "$link"
  fi
}

run_task() {
  local task="$1"
  local gpu="$2"
  local scene variant seed
  IFS='|' read -r scene variant seed <<< "$task"
  variant_inputs "$variant"

  local dataset="dataset/lerf/$scene"
  local name="${scene}_ipr_${variant}_s${seed}"
  local target="$EXTERNAL_ROOT/output/lerf/$name"
  local link="output/lerf/$name"
  local log="$EXTERNAL_ROOT/logs/train/${name}.txt"

  [ -d "$dataset/$MASK_DIR" ] || { echo "Missing $dataset/$MASK_DIR" >&2; return 1; }
  if [ -n "$CONF_DIR" ]; then
    [ -d "$dataset/$CONF_DIR" ] || { echo "Missing $dataset/$CONF_DIR" >&2; return 1; }
  fi
  ensure_model_link "$target" "$link"

  if [ -f "$target/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -f "$target/point_cloud/iteration_30000/classifier.pth" ]; then
    echo "[GPU $gpu] Skip completed: $name"
    return 0
  fi

  local confidence_args=()
  if [ -n "$CONF_DIR" ]; then
    confidence_args=(--object_confidence_path "$CONF_DIR")
  fi

  echo "[GPU $gpu] Training $name (mask=$MASK_DIR confidence=${CONF_DIR:-none})"
  CUDA_VISIBLE_DEVICES="$gpu" python train.py \
    -s "$dataset" \
    -r 1 \
    -m "$link" \
    --config_file config/gaussian_dataset/train.json \
    --train_split \
    --object_path "$MASK_DIR" \
    --seed "$seed" \
    --test_iterations 30000 \
    --save_iterations 30000 \
    "${confidence_args[@]}" 2>&1 | tee "$log"
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
  echo "At least one training worker failed. Inspect $EXTERNAL_ROOT/logs/train." >&2
  exit "$status"
fi

echo "All controlled-ablation training jobs completed."
