#!/usr/bin/env bash
set -euo pipefail

REPORT_ROOT="${REPORT_ROOT:-results/lerf_ovs}"

python script/merge_lerf_ovs_baselines.py \
  --reproduced_by_scene "$REPORT_ROOT/reports/lerf_ovs_standard_by_scene.csv" \
  --metadata "$REPORT_ROOT/reports/lerf_ovs_standard_metadata.json" \
  --published config/lerf_ovs_published_baselines.csv \
  --output_dir "$REPORT_ROOT/reports/comparison"

echo "Comparison: $REPORT_ROOT/reports/comparison/lerf_ovs_comparison.md"
