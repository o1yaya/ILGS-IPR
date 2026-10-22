#!/usr/bin/env bash
set -euo pipefail

# Seed-0 paired check against the released ILGS implementation.
# The baseline is built from the pinned upstream commit. The only baseline
# source change replaces the author's machine-specific language-feature path
# with the equivalent dataset-relative path.

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_official_paper_seed0}"
OFFICIAL_COMMIT="${OFFICIAL_COMMIT:-0dcaae22ad54226763ab3721c97159b03a5764b7}"
SCENES="${SCENES:-ramen figurines teatime}"
VARIANTS="${VARIANTS:-official ipr}"
GPUS="${GPUS:-0 1}"
CLIP_CHECKPOINT="${CLIP_CHECKPOINT:-}"

mkdir -p "$EXTERNAL_ROOT"/{source,code,output,logs/train,logs/eval,reports,audit}
EXTERNAL_ROOT="$(cd "$EXTERNAL_ROOT" && pwd)"

ARCHIVE="$EXTERNAL_ROOT/source/ILGS_release_${OFFICIAL_COMMIT}.zip"
EXTRACT_ROOT="$EXTERNAL_ROOT/source/upstream_${OFFICIAL_COMMIT}"
BASELINE_CODE="$EXTERNAL_ROOT/code/official"
IPR_CODE="$EXTERNAL_ROOT/code/ipr"

download_official_source() {
  if [ ! -s "$ARCHIVE" ]; then
    echo "[source] Downloading official ILGS commit $OFFICIAL_COMMIT"
    curl -L --fail --retry 5 --retry-delay 3 \
      "https://github.com/DCVL-3D/ILGS_release/archive/${OFFICIAL_COMMIT}.zip" \
      -o "$ARCHIVE"
  fi

  if [ ! -d "$EXTRACT_ROOT" ]; then
    mkdir -p "$EXTRACT_ROOT"
    if command -v unzip >/dev/null 2>&1; then
      unzip -q "$ARCHIVE" -d "$EXTRACT_ROOT"
    else
      python -m zipfile -e "$ARCHIVE" "$EXTRACT_ROOT"
    fi
  fi

  UPSTREAM_DIR="$(find "$EXTRACT_ROOT" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$UPSTREAM_DIR" ] && [ -f "$UPSTREAM_DIR/train.py" ] || {
    echo "Could not locate the extracted official ILGS source." >&2
    exit 1
  }
}

link_directory() {
  local target="$1"
  local link="$2"
  mkdir -p "$(dirname "$link")"
  if [ -L "$link" ]; then
    ln -sfn "$target" "$link"
  elif [ -e "$link" ]; then
    echo "Refusing to replace non-symlink path: $link" >&2
    return 1
  else
    ln -s "$target" "$link"
  fi
}

prepare_code_copy() {
  local code="$1"
  local variant="$2"

  if [ ! -f "$code/.prepared_${OFFICIAL_COMMIT}_${variant}" ]; then
    [ ! -e "$code" ] || {
      echo "Incomplete code directory already exists: $code" >&2
      echo "Move it aside, then rerun this script." >&2
      exit 1
    }
    cp -a "$UPSTREAM_DIR" "$code"

    if [ "$variant" = "official" ]; then
      # Portability-only patch: preserve the released tensors and objective.
      sed -i '/data_name = os.path.basename(os.path.normpath(dataset.source_path))/d' "$code/train.py"
      sed -i \
        's|language_feature_dir = f"/mnt/jsm/ILGS/dataset/lerf/{data_name}/language_features_dim3"|language_feature_dir = os.path.join(dataset.source_path, "language_features_dim3")|' \
        "$code/train.py"
    else
      # Start from the same official snapshot and add only the current IPR
      # training implementation plus its argument and deterministic-seed hook.
      cp "$SOURCE_ROOT/train.py" "$code/train.py"
      cp "$SOURCE_ROOT/arguments/__init__.py" "$code/arguments/__init__.py"
      cp "$SOURCE_ROOT/utils/general_utils.py" "$code/utils/general_utils.py"
    fi

    touch "$code/.prepared_${OFFICIAL_COMMIT}_${variant}"
  fi

  # Keep evaluation-only compatibility fixes synchronized on every resume.
  cp "$SOURCE_ROOT/segmentation_mask_official_eval.py" "$code/segmentation_mask_eval.py"

  link_directory "$SOURCE_ROOT/dataset" "$code/dataset"
  mkdir -p "$code/autoencoder/ckpt"
  link_directory "$SOURCE_ROOT/autoencoder/ckpt/lerf" "$code/autoencoder/ckpt/lerf"
  mkdir -p "$code/output/lerf"
}

audit_inputs() {
  local failed=0
  for scene in $SCENES; do
    local dataset="$SOURCE_ROOT/dataset/lerf/$scene"
    for path in \
      "$dataset/images" \
      "$dataset/images_train" \
      "$dataset/object_mask" \
      "$dataset/language_features_dim3" \
      "$dataset/test_mask" \
      "$SOURCE_ROOT/autoencoder/ckpt/lerf/$scene/best_ckpt.pth"; do
      if [ ! -e "$path" ]; then
        echo "Missing required official-protocol input: $path" >&2
        failed=1
      fi
    done

    for path in \
      "$dataset/object_mask_refined_trainonly_strict" \
      "$dataset/object_confidence_ipr_trainview_consistency_strict"; do
      if [ ! -d "$path" ]; then
        echo "Missing required IPR input: $path" >&2
        failed=1
      fi
    done
  done
  if [ -n "$CLIP_CHECKPOINT" ] && [ ! -s "$CLIP_CHECKPOINT" ]; then
    echo "Local OpenCLIP checkpoint not found: $CLIP_CHECKPOINT" >&2
    failed=1
  fi
  [ "$failed" -eq 0 ] || exit 1
}

variant_code() {
  case "$1" in
    official) echo "$BASELINE_CODE" ;;
    ipr) echo "$IPR_CODE" ;;
    *) echo "Unknown variant: $1" >&2; return 1 ;;
  esac
}

prepare_model_link() {
  local code="$1"
  local scene="$2"
  local variant="$3"
  local target="$EXTERNAL_ROOT/output/$variant/$scene"
  local link="$code/output/lerf/$scene"
  mkdir -p "$target"
  link_directory "$target" "$link"
}

run_task() {
  local task="$1"
  local gpu="$2"
  local scene variant code target train_log eval_log
  IFS='|' read -r scene variant <<< "$task"
  code="$(variant_code "$variant")"
  target="$EXTERNAL_ROOT/output/$variant/$scene"
  train_log="$EXTERNAL_ROOT/logs/train/${scene}_${variant}_s0.txt"
  eval_log="$EXTERNAL_ROOT/logs/eval/${scene}_${variant}_s0.txt"

  prepare_model_link "$code" "$scene" "$variant"

  if [ -s "$target/point_cloud/iteration_30000/point_cloud.ply" ] \
    && [ -s "$target/point_cloud/iteration_30000/classifier.pth" ]; then
    echo "[GPU $gpu] Skip completed training: $scene $variant seed 0"
  else
    echo "[GPU $gpu] Train: $scene $variant seed 0"
    (
      cd "$code"
      if [ "$variant" = "official" ]; then
        CUDA_VISIBLE_DEVICES="$gpu" python train.py \
          -s "dataset/lerf/$scene" \
          -r 1 \
          -m "output/lerf/$scene" \
          --config_file config/gaussian_dataset/train.json \
          --train_split \
          --object_path object_mask \
          --test_iterations 30000 \
          --save_iterations 30000
      else
        CUDA_VISIBLE_DEVICES="$gpu" python train.py \
          -s "dataset/lerf/$scene" \
          -r 1 \
          -m "output/lerf/$scene" \
          --config_file config/gaussian_dataset/train.json \
          --train_split \
          --object_path object_mask_refined_trainonly_strict \
          --object_confidence_path object_confidence_ipr_trainview_consistency_strict \
          --seed 0 \
          --test_iterations 30000 \
          --save_iterations 30000
      fi
    ) 2>&1 | tee "$train_log"
  fi

  echo "[GPU $gpu] Released decoding/evaluation: $scene $variant"
  (
    cd "$code"
    clip_args=()
    if [ -n "$CLIP_CHECKPOINT" ]; then
      clip_args=(--clip_checkpoint "$CLIP_CHECKPOINT")
    fi
    CUDA_VISIBLE_DEVICES="$gpu" python render_all.py \
      -m "output/lerf/$scene" --skip_train --object_path object_mask
    CUDA_VISIBLE_DEVICES="$gpu" python feature_projector.py "lerf/$scene"
    CUDA_VISIBLE_DEVICES="$gpu" python segmentation_mask_eval.py \
      -m "output/lerf/$scene" "${clip_args[@]}"
    python script/eval_lerf_mask.py -m "output/lerf/$scene"
  ) 2>&1 | tee "$eval_log"
}

download_official_source
prepare_code_copy "$BASELINE_CODE" official
prepare_code_copy "$IPR_CODE" ipr
audit_inputs

cat > "$EXTERNAL_ROOT/audit/protocol.txt" <<EOF
Official ILGS commit: $OFFICIAL_COMMIT
Seed: 0 (the released code fixes all RNGs to zero)
Scenes: $SCENES
Variants: $VARIANTS
Resolution: -r 1
Iterations: 30000
Split: released --train_split using images_train
Baseline masks: object_mask
IPR masks: object_mask_refined_trainonly_strict
IPR confidence: object_confidence_ipr_trainview_consistency_strict
Decoder: released progressive mask expansion; only query/file naming is made GT-compatible
OpenCLIP checkpoint: ${CLIP_CHECKPOINT:-open_clip cache / registry default}
Evaluation: released script/eval_lerf_mask.py
Baseline portability patch: machine-specific language-feature path -> dataset-relative equivalent
EOF

sha256sum \
  "$BASELINE_CODE/train.py" \
  "$IPR_CODE/train.py" \
  "$BASELINE_CODE/segmentation_mask_eval.py" \
  "$BASELINE_CODE/script/eval_lerf_mask.py" \
  > "$EXTERNAL_ROOT/audit/source_sha256.txt"

diff -u "$UPSTREAM_DIR/train.py" "$BASELINE_CODE/train.py" \
  > "$EXTERNAL_ROOT/audit/baseline_portability_only.patch" || true

TASKS=()
for scene in $SCENES; do
  for variant in $VARIANTS; do
    TASKS+=("$scene|$variant")
  done
done

read -r -a GPU_LIST <<< "$GPUS"
[ "${#GPU_LIST[@]}" -gt 0 ] || { echo "No GPUs specified." >&2; exit 1; }

pids=()
worker() {
  local worker_index="$1"
  local gpu="$2"
  local stride="${#GPU_LIST[@]}"
  local index
  for ((index=worker_index; index<${#TASKS[@]}; index+=stride)); do
    run_task "${TASKS[$index]}" "$gpu"
  done
}

for index in "${!GPU_LIST[@]}"; do
  worker "$index" "${GPU_LIST[$index]}" &
  pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then status=1; fi
done

if [ "$status" -ne 0 ]; then
  echo "At least one official-protocol worker failed. Inspect $EXTERNAL_ROOT/logs." >&2
  exit "$status"
fi

python "$SOURCE_ROOT/script/summarize_official_paper_protocol_seed0.py" \
  --root "$EXTERNAL_ROOT" \
  --scenes $SCENES \
  --variants $VARIANTS

echo "Official-protocol seed-0 experiment complete."
echo "Report: $EXTERNAL_ROOT/reports/official_paper_protocol_seed0.md"
