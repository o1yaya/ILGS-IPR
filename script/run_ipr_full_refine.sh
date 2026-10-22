#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: CUDA_VISIBLE_DEVICES=0 bash script/run_ipr_full_refine.sh output/lerf/<scene>_refined_masks [--save_candidates]"
  echo
  echo "Example:"
  echo "  CUDA_VISIBLE_DEVICES=0 bash script/run_ipr_full_refine.sh output/lerf/figurines_refined_masks --save_candidates"
  exit 1
fi

MODEL_PATH="$1"
shift || true
EXTRA_ARGS=("$@")

if [ ! -d "$MODEL_PATH" ]; then
  echo "Error: model path not found: $MODEL_PATH" >&2
  exit 1
fi

SCENE=""
case "$MODEL_PATH" in
  *"/teatime"*|*"\\teatime"*|*"/teatime_refined_masks"*|*"\\teatime_refined_masks"*) SCENE="teatime" ;;
  *"/figurines"*|*"\\figurines"*|*"/figurines_refined_masks"*|*"\\figurines_refined_masks"*) SCENE="figurines" ;;
  *"/ramen"*|*"\\ramen"*|*"/ramen_refined_masks"*|*"\\ramen_refined_masks"*) SCENE="ramen" ;;
esac

if [ -z "$SCENE" ]; then
  echo "Error: could not infer LERF scene from model path: $MODEL_PATH" >&2
  echo "Supported scenes: teatime, figurines, ramen" >&2
  exit 1
fi

BASE_PATH="$MODEL_PATH/test/ours_30000_text"
FEATURE_DIR="$BASE_PATH/feature_map_npy"
LOGITS_DIR="$BASE_PATH/logits"

if [ ! -d "$FEATURE_DIR" ] || [ -z "$(find "$FEATURE_DIR" -maxdepth 1 -name '*.npy' -print -quit)" ]; then
  echo "Error: rendered feature maps not found in: $FEATURE_DIR" >&2
  echo "Run render_all.py on the IPR output first, for example:" >&2
  echo "  CUDA_VISIBLE_DEVICES=0 python render_all.py -m $MODEL_PATH --skip_train --train_split" >&2
  exit 1
fi

if [ ! -d "$LOGITS_DIR" ] || [ -z "$(find "$LOGITS_DIR" -maxdepth 1 -name '*_logits.npy' -print -quit)" ]; then
  echo "Error: rendered identity logits not found in: $LOGITS_DIR" >&2
  echo "Run render_all.py on the IPR output first." >&2
  exit 1
fi

# eval_lerf_mask.py derives the GT path by replacing the first "output" with
# "dataset".  For outputs such as output/lerf/ramen_refined_masks, create a
# dataset alias pointing back to the original scene so the repository evaluator
# can be reused without modification.
DATASET_ALIAS="${MODEL_PATH/output/dataset}"
DATASET_ALIAS_DIR="$(dirname "$DATASET_ALIAS")"
DATASET_SOURCE="dataset/lerf/$SCENE"
if [ ! -e "$DATASET_ALIAS" ]; then
  mkdir -p "$DATASET_ALIAS_DIR"
  ln -sfn "$SCENE" "$DATASET_ALIAS"
  echo "Created dataset alias: $DATASET_ALIAS -> $SCENE"
fi

export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

echo "Scene:       $SCENE"
echo "Model path:  $MODEL_PATH"
echo "Features:    $FEATURE_DIR"
echo "Logits:      $LOGITS_DIR"
echo "GT alias:    $DATASET_ALIAS"
echo

rm -rf "$BASE_PATH/test_mask"

python segmentation_mask_full_refine.py \
  -m "$MODEL_PATH" \
  "${EXTRA_ARGS[@]}"

mkdir -p logs
LOG_SAFE_NAME="$(echo "$MODEL_PATH" | tr '/\\' '__')"
EVAL_LOG="logs/eval_${LOG_SAFE_NAME}_full_refine.txt"

python script/eval_lerf_mask.py -m "$MODEL_PATH" | tee "$EVAL_LOG"

echo
echo "Full-refine masks: $BASE_PATH/test_mask"
echo "Debug json:        $BASE_PATH/full_refine_debug.json"
echo "Eval log:          $EVAL_LOG"

