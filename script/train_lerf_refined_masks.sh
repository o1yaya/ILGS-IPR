#!/bin/bash
set -e

case "$#" in
    2)
        dataset_name="$1"
        scale="$2"
        ;;
    *)
        echo "Usage: $0 <dataset_name> <scale>" >&2
        exit 1
        ;;
esac

dataset_folder="dataset/$dataset_name"

if [ ! -d "$dataset_folder" ]; then
    echo "Error: Cannot find dataset directory at '$dataset_folder'." >&2
    exit 2
fi

if [ ! -d "$dataset_folder/object_mask_refined" ]; then
    echo "Error: '$dataset_folder/object_mask_refined' not found. Run refine_object_masks.py first." >&2
    exit 3
fi

if [ ! -d "$dataset_folder/object_confidence_refined" ]; then
    echo "Error: '$dataset_folder/object_confidence_refined' not found. Run refine_object_masks.py first." >&2
    exit 4
fi

echo "Dataset: $dataset_name, Scale: $scale, Path: $dataset_folder ... ready to process with refined object masks."

python train.py \
    -s "$dataset_folder" \
    -r "$scale" \
    -m "output/${dataset_name}_refined_masks" \
    --config_file config/gaussian_dataset/train.json \
    --train_split \
    --object_path object_mask_refined \
    --object_confidence_path object_confidence_refined

python render.py \
    -m "output/${dataset_name}_refined_masks" \
    --num_classes 256 \
    --images images
