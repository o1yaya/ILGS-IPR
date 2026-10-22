# IPR threshold sensitivity experiment

This experiment evaluates the fixed consistency threshold at:

`0.65, 0.70, 0.75, 0.80, 0.85`

The default run uses seed 0 on:

- LERF-Mask: `ramen figurines teatime`
- 3D-OVS: `bench covered_desk snacks`

All threshold-specific confidence maps, models, logs, and reports use unique names. Existing
`strict_trainview_consistency` results are not overwritten.

## Run on the server

```bash
cd ~/vsproject1/ILGS_release-main
conda activate ILGS

chmod +x \
  script/prepare_ipr_threshold_sensitivity.sh \
  script/run_ipr_threshold_sensitivity_2gpu.sh

ROOT=/media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity
mkdir -p "$ROOT"

nohup env ROOT="$ROOT" \
  bash script/run_ipr_threshold_sensitivity_2gpu.sh \
  > "$ROOT/launcher.log" 2>&1 < /dev/null &
```

Monitor progress:

```bash
tail -f /media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity/launcher.log
```

## Resume selected stages

Completed training and evaluation tasks are skipped automatically.

```bash
ROOT=/media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity \
STAGES="train eval summarize" \
bash script/run_ipr_threshold_sensitivity_2gpu.sh
```

To regenerate only the reports:

```bash
ROOT=/media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity \
STAGES="summarize" \
bash script/run_ipr_threshold_sensitivity_2gpu.sh
```

## Final reports

```bash
cat /media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity/lerf_mask/reports/threshold_sensitivity/threshold_sensitivity_summary.md

cat /media/cx/data/cxdata/ilgs_ipr_threshold_sensitivity/3dovs/reports/threshold_sensitivity/threshold_sensitivity_summary.md
```

The reports contain per-scene mIoU/mBIoU, the scene mean, the fraction of low-semantic
identity tracks, the fraction of large-region tracks, and the fraction of pixels whose final
confidence is below one.
