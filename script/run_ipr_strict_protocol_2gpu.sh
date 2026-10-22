#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_ipr_strict_protocol}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf}"
SCENES="${SCENES:-figurines ramen teatime}"
SEEDS="${SEEDS:-0 1 2}"
RESOLUTION="${RESOLUTION:-1}"
VARIANTS="${VARIANTS:-strict_official strict_allview_evalvocab strict_trainview_evalvocab strict_trainview_independent}"
ALLVIEW_CONF_DIR="${ALLVIEW_CONF_DIR:-object_confidence_ipr_no_visibility}"
REUSE_CURRENT_MODELS="${REUSE_CURRENT_MODELS:-0}"

mkdir -p "$EXTERNAL_ROOT/output/lerf" "$EXTERNAL_ROOT/logs/train" output/lerf
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"

variant_inputs() {
  case "$1" in
    official)
      MASK_DIR="object_mask"; CONF_DIR="" ;;
    strict_official)
      MASK_DIR="object_mask"; CONF_DIR="" ;;
    strict_allview_evalvocab)
      MASK_DIR="object_mask_refined"; CONF_DIR="$ALLVIEW_CONF_DIR" ;;
    strict_trainview_evalvocab)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_evalvocab_strict" ;;
    strict_trainview_independent)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_independent_strict" ;;
    strict_trainview_areaonly)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_areaonly_strict" ;;
    strict_trainview_consistency)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_consistency_strict" ;;
    strict_trainview_consistency_t[0-9][0-9][0-9])
      threshold_code="${1##*_t}"
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_ipr_trainview_consistency_t${threshold_code}" ;;
    strict_trainview_cleanup)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="" ;;
    strict_trainview_cleanup_conf)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_refined_trainonly_strict" ;;
    strict_trainview_consistency_only)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_consistency_only_strict" ;;
    strict_trainview_large_only)
      MASK_DIR="object_mask_refined_trainonly_strict"; CONF_DIR="object_confidence_ipr_trainview_large_only_strict" ;;
    *) echo "Unknown strict-protocol variant: $1" >&2; return 1 ;;
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

  local dataset="$DATASET_ROOT/$scene"
  local name="${scene}_ipr_${variant}_s${seed}"
  local target="$EXTERNAL_ROOT/output/lerf/$name"
  local link="output/lerf/$name"
  local log="$EXTERNAL_ROOT/logs/train/${name}.txt"

  if [ "$REUSE_CURRENT_MODELS" = "1" ] && [ -L "$link" ]; then
    local current_target
    current_target="$(readlink -f "$link")"
    if [ -s "$current_target/point_cloud/iteration_30000/point_cloud.ply" ] \
      && [ -s "$current_target/point_cloud/iteration_30000/classifier.pth" ]; then
      target="$current_target"
      echo "[GPU $gpu] Reusing current completed model: $name -> $target"
    fi
  fi

  [ -d "$dataset/$MASK_DIR" ] || { echo "Missing $dataset/$MASK_DIR" >&2; return 1; }
  if [ -n "$CONF_DIR" ]; then
    [ -d "$dataset/$CONF_DIR" ] || { echo "Missing $dataset/$CONF_DIR" >&2; return 1; }
  fi
  ensure_model_link "$target" "$link"

  if [ -s "$target/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -s "$target/point_cloud/iteration_30000/classifier.pth" ]; then
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
    -r "$RESOLUTION" \
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

worker 0 0 & pid0=$!
worker 1 1 & pid1=$!
status=0
if ! wait "$pid0"; then status=1; fi
if ! wait "$pid1"; then status=1; fi
[ "$status" -eq 0 ] || { echo "At least one strict-protocol training worker failed." >&2; exit "$status"; }
echo "All strict-protocol training jobs completed."
