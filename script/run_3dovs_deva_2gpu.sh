#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

DATASET_ROOT="${DATASET_ROOT:-dataset/3dovs}"
DEVA_ROOT="${DEVA_ROOT:-/home/cx/PycharmProjects/PythonProject1/Gaussian-Extracting/Tracking-Anything-with-DEVA}"
TORCH_HOME="${TORCH_HOME:-/media/cx/data/cxdata/torch_cache}"
LOG_ROOT="${LOG_ROOT:-/media/cx/data/cxdata/ilgs_3dovs/logs/deva}"
SCENES="${SCENES:-bed bench blue_sofa covered_desk lawn office_desk room snacks sofa table}"
SAM_POINTS_PER_SIDE="${SAM_POINTS_PER_SIDE:-32}"
SAM_POINTS_PER_BATCH="${SAM_POINTS_PER_BATCH:-4}"

export TORCH_HOME
export PYTHONPATH="$DEVA_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-max_split_size_mb:128}"
mkdir -p "$LOG_ROOT"

python script/prepare_3dovs_layout.py \
  --dataset_root "$DATASET_ROOT" \
  --scenes $SCENES

for scene in $SCENES; do
  python script/prepare_deva_resized_images.py \
    --src "$DATASET_ROOT/$scene/images" \
    --dst "$DATASET_ROOT/$scene/images_deva_480" \
    --min_side 480
done

TASKS=($SCENES)

count_images() {
  find "$1" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | wc -l
}

run_task() {
  local scene="$1" gpu="$2"
  local dataset="$DATASET_ROOT/$scene"
  local expected actual
  expected="$(count_images "$dataset/images")"
  actual=0
  if [ -d "$dataset/object_mask_deva_raw" ]; then
    actual="$(find "$dataset/object_mask_deva_raw" -maxdepth 1 -type f -iname '*.png' | wc -l)"
  fi
  if [ "$actual" -eq "$expected" ]; then
    echo "[GPU $gpu] Skip completed DEVA masks: $scene ($actual/$expected)"
    return 0
  fi

  echo "[GPU $gpu] Running DEVA: $scene"
  DEVA_IMAGE_DIR=images_deva_480 \
  SAM_POINTS_PER_SIDE="$SAM_POINTS_PER_SIDE" \
  SAM_POINTS_PER_BATCH="$SAM_POINTS_PER_BATCH" \
  CUDA_VISIBLE_DEVICES="$gpu" \
  bash script/run_deva_object_masks.sh \
    "3dovs/$scene" 1 "$DEVA_ROOT" object_mask_deva_raw \
    2>&1 | tee "$LOG_ROOT/${scene}.txt"
}

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
  echo "At least one DEVA worker failed. Inspect $LOG_ROOT." >&2
  exit "$status"
}

echo "All requested 3D-OVS DEVA masks are ready."
