#!/bin/bash
set -e

if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "Usage: $0 <dataset_name> <scale> <deva_root> [output_dir_name]" >&2
    echo "Example: CUDA_VISIBLE_DEVICES=0 bash script/run_deva_object_masks.sh lerf/figurines 1 /path/to/Tracking-Anything-with-DEVA object_mask_deva_raw" >&2
    exit 1
fi

dataset_name="$1"
scale="$2"
deva_root="$3"
output_dir_name="${4:-object_mask_deva_raw}"
sam_points_per_side="${SAM_POINTS_PER_SIDE:-32}"
sam_points_per_batch="${SAM_POINTS_PER_BATCH:-4}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dataset_folder="$repo_root/dataset/$dataset_name"

if [ ! -d "$dataset_folder" ]; then
    echo "Error: dataset folder not found: $dataset_folder" >&2
    exit 2
fi

if [ ! -d "$deva_root" ]; then
    echo "Error: DEVA root not found: $deva_root" >&2
    exit 3
fi

if [ ! -f "$deva_root/deva/inference/inference_core.py" ]; then
    echo "Error: '$deva_root' does not look like the DEVA repository root." >&2
    echo "Expected: $deva_root/deva/inference/inference_core.py" >&2
    exit 3
fi

export PYTHONPATH="$deva_root${PYTHONPATH:+:$PYTHONPATH}"

if [ -n "${DEVA_IMAGE_DIR:-}" ]; then
    if [[ "$DEVA_IMAGE_DIR" = /* ]]; then
        img_path="$DEVA_IMAGE_DIR"
    else
        img_path="$dataset_folder/$DEVA_IMAGE_DIR"
    fi
elif [ "$scale" = "1" ]; then
    img_path="$dataset_folder/images"
else
    img_path="$dataset_folder/images_${scale}"
fi

if [ ! -d "$img_path" ]; then
    echo "Error: image directory not found: $img_path" >&2
    exit 4
fi

deva_dataset_key="${dataset_name//\//_}"
deva_output="$deva_root/example/output_gaussian_dataset/$deva_dataset_key"

cd "$deva_root"

common_args=(
    --chunk_size 4
    --img_path "$img_path"
    --amp
    --temporal_setting semionline
    --size 480
    --output "$deva_output"
    --suppress_small_objects
    --SAM_PRED_IOU_THRESHOLD 0.1
    --SAM_NUM_POINTS_PER_SIDE "$sam_points_per_side"
    --SAM_NUM_POINTS_PER_BATCH "$sam_points_per_batch"
)

if python demo/demo_automatic.py -h 2>&1 | grep -q -- "--use_short_id"; then
    python demo/demo_automatic.py "${common_args[@]}" --use_short_id
else
    echo "Info: this DEVA demo_automatic.py has no --use_short_id option; running without it."
    python demo/demo_automatic.py "${common_args[@]}"
fi

if [ ! -d "$deva_output/Annotations" ]; then
    echo "Error: DEVA did not create $deva_output/Annotations" >&2
    exit 5
fi

rm -rf "$dataset_folder/$output_dir_name"
mkdir -p "$dataset_folder/$output_dir_name"
cp -r "$deva_output/Annotations/." "$dataset_folder/$output_dir_name/"

echo "DEVA masks copied to: $dataset_folder/$output_dir_name"
