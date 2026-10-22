#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

OPENCLIP_CHECKPOINT="${OPENCLIP_CHECKPOINT:-checkpoints/open_clip_pytorch_model.bin}"
DATASET_ROOT="${DATASET_ROOT:-dataset/lerf_ovs}"
LABEL_ROOT="${LABEL_ROOT:-$DATASET_ROOT/label}"
MODEL_ROOT="${MODEL_ROOT:-output/lerf_ovs}"
AUTOENCODER_ROOT="${AUTOENCODER_ROOT:-autoencoder/ckpt/lerf}"
REPORT_ROOT="${REPORT_ROOT:-results/lerf_ovs}"
SCENES="${SCENES:-waldo_kitchen ramen figurines teatime}"
MODEL_VARIANTS="${MODEL_VARIANTS:-${METHODS:-official no_visibility}}"
SEEDS="${SEEDS:-0}"
MASK_MODE="${MASK_MODE:-seed_ref}"

[ -f "$OPENCLIP_CHECKPOINT" ] || { echo "Missing OpenCLIP checkpoint: $OPENCLIP_CHECKPOINT" >&2; exit 1; }
mkdir -p "$REPORT_ROOT/audit" "$REPORT_ROOT/runs" "$REPORT_ROOT/logs"

set +e
python script/audit_lerf_ovs_reuse.py \
  --dataset_root "$DATASET_ROOT" \
  --label_root "$LABEL_ROOT" \
  --model_root "$MODEL_ROOT" \
  --methods $MODEL_VARIANTS \
  --seeds $SEEDS \
  --scenes $SCENES \
  --output "$REPORT_ROOT/audit/checkpoint_reuse.json"
audit_status=$?
set -e
if [ "$audit_status" -ne 0 ]; then
  echo "LERF-OVS reuse audit failed. Read $REPORT_ROOT/audit/checkpoint_reuse.json" >&2
  echo "This usually means the current LERF-Mask checkpoints cannot be reported as standard LERF-OVS results." >&2
  exit "$audit_status"
fi

find_gt() {
  local scene="$1"
  if [ -d "$LABEL_ROOT/$scene/gt" ]; then
    printf '%s\n' "$LABEL_ROOT/$scene/gt"
  else
    printf '%s\n' "$LABEL_ROOT/$scene"
  fi
}

method_label() {
  case "$1" in
    no_visibility|ipr) printf '%s\n' "ipr" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

run_task() {
  local task="$1"
  local gpu="$2"
  local scene variant seed method
  IFS='|' read -r scene variant seed <<< "$task"
  method="$(method_label "$variant")"
  local name="${scene}_ipr_${variant}_s${seed}"
  local model="$MODEL_ROOT/$name"
  local dataset="$DATASET_ROOT/$scene"
  local gt
  gt="$(find_gt "$scene")"
  local run_dir="$REPORT_ROOT/runs/$name"
  local query_file="$REPORT_ROOT/audit/${scene}_queries.txt"
  local frame_file="$REPORT_ROOT/audit/${scene}_frames.txt"
  local mask_dir="$model/lerf_ovs_standard_masks_${MASK_MODE}"
  local train_frame_map="$model/train/ours_30000_text/frame_names.json"
  local test_frame_map="$model/test/ours_30000_text/frame_names.json"
  local ae="$AUTOENCODER_ROOT/$scene/best_ckpt.pth"

  mkdir -p "$run_dir"
  python script/build_query_file_from_masks.py \
    --gt_path "$gt" --output "$query_file" --frame_output "$frame_file"
  [ -f "$ae" ] || { echo "Missing autoencoder checkpoint: $ae" >&2; return 1; }

  if [ ! -f "$train_frame_map" ] || [ ! -f "$test_frame_map" ]; then
    echo "[GPU $gpu] Rendering train and held-out cameras for $name"
    CUDA_VISIBLE_DEVICES="$gpu" python render_all.py \
      -s "$dataset" -m "$model" --train_split --frame_file "$frame_file"
  fi

  for split in train test; do
    frame_map="$model/$split/ours_30000_text/frame_names.json"
    logits_dir="$model/$split/ours_30000_text/logits"
    [ -d "$logits_dir" ] || { echo "Missing rendered logits: $logits_dir" >&2; return 1; }
    echo "[GPU $gpu] Decoding $split cameras for $name"
    CUDA_VISIBLE_DEVICES="$gpu" python segmentation_mask_stream.py \
      -m "$model" \
      --dataset_name "$scene" \
      --query_file "$query_file" \
      --autoencoder_checkpoint "$ae" \
      --clip_checkpoint "$OPENCLIP_CHECKPOINT" \
      --mode "$MASK_MODE" \
      --render_split "$split" \
      --frame_map "$frame_map" \
      --frame_file "$frame_file" \
      --output_dir "$mask_dir"
  done

  python script/eval_lerf_ovs_standard.py \
    --gt_path "$gt" \
    --pred_path "$mask_dir" \
    --output_dir "$run_dir" \
    --scene "$scene" \
    --method "$method" \
    --seed "$seed" 2>&1 | tee "$REPORT_ROOT/logs/${name}.txt"
}

TASKS=()
for scene in $SCENES; do
  for method in $MODEL_VARIANTS; do
    for seed in $SEEDS; do
      TASKS+=("$scene|$method|$seed")
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
[ "$status" -eq 0 ] || { echo "At least one standard LERF-OVS evaluation failed." >&2; exit "$status"; }

REPORT_METHODS=()
for variant in $MODEL_VARIANTS; do
  label="$(method_label "$variant")"
  if [[ " ${REPORT_METHODS[*]} " != *" $label "* ]]; then
    REPORT_METHODS+=("$label")
  fi
done

python script/summarize_lerf_ovs_standard.py \
  --runs_dir "$REPORT_ROOT/runs" \
  --output_dir "$REPORT_ROOT/reports" \
  --scenes $SCENES \
  --methods "${REPORT_METHODS[@]}"

echo "Report: $REPORT_ROOT/reports/lerf_ovs_standard_summary.md"
