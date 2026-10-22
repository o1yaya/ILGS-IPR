#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_3dovs}"
REUSE_ROOT="${REUSE_ROOT:-}"
DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
SCENES="${SCENES:-bed}"
VARIANTS="${VARIANTS:-official ipr}"
SEEDS="${SEEDS:-0}"
RESOLUTION="${RESOLUTION:-4}"

mkdir -p "$EXTERNAL_ROOT/output/3dovs" "$EXTERNAL_ROOT/logs/train" output/3dovs
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"
if [ -n "$REUSE_ROOT" ]; then
  [ -d "$REUSE_ROOT" ] || { echo "Missing reuse root: $REUSE_ROOT" >&2; exit 1; }
  REUSE_ROOT="$(cd "$REUSE_ROOT" && pwd)"
fi

variant_inputs() {
  case "$1" in
    official) MASK_DIR="object_mask";         CONF_DIR="" ;;
    ipr)      MASK_DIR="object_mask_refined"; CONF_DIR="object_confidence_ipr" ;;
    strict_trainview_consistency)
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_ipr_trainview_consistency_strict" ;;
    strict_trainview_consistency_t[0-9][0-9][0-9])
      threshold_code="${1##*_t}"
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_ipr_trainview_consistency_t${threshold_code}" ;;
    strict_trainview_cleanup)
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="" ;;
    strict_trainview_cleanup_conf)
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_refined_trainonly_strict" ;;
    strict_trainview_consistency_only)
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_ipr_trainview_consistency_only_strict" ;;
    strict_trainview_large_only)
      MASK_DIR="object_mask_refined_trainonly_strict"
      CONF_DIR="object_confidence_ipr_trainview_large_only_strict" ;;
    *) echo "Unknown variant: $1" >&2; return 1 ;;
  esac
}

ensure_model_link() {
  local target="$1" link="$2"
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
  local task="$1" gpu="$2"
  local scene variant seed
  IFS='|' read -r scene variant seed <<< "$task"
  variant_inputs "$variant"

  local dataset="$DATASET_ROOT/$scene"
  local name="${scene}_ipr_${variant}_s${seed}"
  local target="$EXTERNAL_ROOT/output/3dovs/$name"
  local link="output/3dovs/$name"
  local log="$EXTERNAL_ROOT/logs/train/${name}.txt"

  if [ -n "$REUSE_ROOT" ]; then
    local reuse_target="$REUSE_ROOT/output/3dovs/$name"
    if [ -s "$reuse_target/point_cloud/iteration_30000/point_cloud.ply" ] \
      && [ -s "$reuse_target/point_cloud/iteration_30000/classifier.pth" ]; then
      target="$reuse_target"
      echo "[GPU $gpu] Reusing completed model: $name"
    fi
  fi

  [ -d "$dataset/$MASK_DIR" ] || { echo "Missing $dataset/$MASK_DIR" >&2; return 1; }
  [ -d "$dataset/language_features_dim3" ] || {
    echo "Missing $dataset/language_features_dim3" >&2
    return 1
  }
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
  echo "At least one 3D-OVS training worker failed. Inspect $EXTERNAL_ROOT/logs/train." >&2
  exit "$status"
}
echo "All 3D-OVS training jobs completed."
