#!/bin/bash
set -e

case "$#" in
    2)
        dataset_name="$1"
        scale="$2"
        ;;
    *)
        echo "Usage: $0 <dataset_name> <scale>" >&2
        echo "Example: CUDA_VISIBLE_DEVICES=0 bash script/train_lerf_v2anchor_masks.sh lerf/figurines 1" >&2
        exit 1
        ;;
esac

dataset_folder="dataset/$dataset_name"

if [ ! -d "$dataset_folder" ]; then
    echo "Error: Cannot find dataset directory at '$dataset_folder'." >&2
    exit 2
fi

if [ ! -d "$dataset_folder/object_mask_v2anchor_refined" ]; then
    echo "Error: '$dataset_folder/object_mask_v2anchor_refined' not found. Run refine_object_masks_v2anchor.py first." >&2
    exit 3
fi

if [ ! -d "$dataset_folder/object_confidence_v2anchor_refined" ]; then
    echo "Error: '$dataset_folder/object_confidence_v2anchor_refined' not found. Run refine_object_masks_v2anchor.py first." >&2
    exit 4
fi

echo "Dataset: $dataset_name, Scale: $scale, Path: $dataset_folder ... ready to process with V2-Anchor refined object masks."

python train.py \
    -s "$dataset_folder" \
    -r "$scale" \
    -m "output/${dataset_name}_v2anchor_masks" \
    --config_file config/gaussian_dataset/train.json \
    --train_split \
    --object_path object_mask_v2anchor_refined \
    --object_confidence_path object_confidence_v2anchor_refined

python render.py \
    -m "output/${dataset_name}_v2anchor_masks" \
    --num_classes 256 \
    --images images
