#!/usr/bin/env bash
set -euo pipefail

EXTERNAL_ROOT="${EXTERNAL_ROOT:-/media/cx/data/cxdata/ilgs_3dovs}"
SCENES="${SCENES:-bench blue_sofa office_desk covered_desk sofa}"
SEEDS="${SEEDS:-1 2}"
REPORT_DIR="${REPORT_DIR:-$EXTERNAL_ROOT/reports/five_scene_multiseed}"

export EXTERNAL_ROOT SCENES SEEDS REPORT_DIR
export VARIANTS="official ipr"
export RESOLUTION=4

echo "Training scenes: $SCENES"
echo "New seeds: $SEEDS"
bash script/run_3dovs_controlled_2gpu.sh

echo "Evaluating with the common seed_ref decoder..."
bash script/eval_3dovs_controlled_2gpu.sh

echo "Five-scene report: $REPORT_DIR/controlled_ablation_summary.md"
