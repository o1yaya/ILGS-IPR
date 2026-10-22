# Final manuscript experiments

This file is the single source of truth for the experiments reported in the
manuscript. Run all commands from the repository root in the `ILGS` Conda
environment.

## Method definition

- Final variant: `strict_trainview_consistency`
- Semantic-consistency threshold: `0.75`
- Training views only are used to estimate reliability.
- Identity IDs are preserved. IPR changes the identity-loss weight only.
- Main results use seeds `0 1 2`.
- LERF-Mask resolution: `1`; 3D-OVS resolution: `4`.
- OpenCLIP checkpoint: `/media/cx/data/cxdata/models/openclip/open_clip_pytorch_model.bin`

Load the canonical paths and scene lists:

```bash
set -a
source config/experiments/paper_final.env
set +a
```

## Final IPR preprocessing

Both datasets use the same query-free consistency definition and the same
threshold from `paper_final.env`.

```bash
DATASET_ROOT="$LERF_DATASET_ROOT" \
SCENES="$LERF_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_ipr_strict_protocol.sh

DATASET_ROOT="$OVS_DATASET_ROOT" \
SCENES="$OVS_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_3dovs_ipr_consistency.sh
```

## LERF-Mask main comparison

The manuscript table uses the `official` row from
`$LERF_BASELINE_ROOT/reports/controlled_ablation_summary.md` and the
`strict_trainview_consistency` row from
`$LERF_MAIN_ROOT/reports/controlled_ablation_summary.md`. These rows share the
same controlled training and evaluation definition.

```bash
EXTERNAL_ROOT="$LERF_MAIN_ROOT" \
DATASET_ROOT="$LERF_DATASET_ROOT" \
SCENES="$LERF_SCENES" \
VARIANTS="$LERF_VARIANT" \
SEEDS="$LERF_SEEDS" \
RESOLUTION=1 \
bash script/run_ipr_strict_protocol_2gpu.sh
```

## 3D-OVS main comparison

The controlled baseline checkpoints are under `$OVS_BASELINE_ROOT`; the final
IPR checkpoints are under `$OVS_MAIN_ROOT`. The manuscript's combined
ten-scene table is stored in
`$OVS_MAIN_ROOT/reports_three_seed/controlled_ablation_summary.md`.

```bash
EXTERNAL_ROOT="$OVS_MAIN_ROOT" \
DATASET_ROOT="$OVS_DATASET_ROOT" \
SCENES="$OVS_SCENES" \
VARIANTS="$OVS_VARIANT" \
SEEDS="$OVS_SEEDS" \
RESOLUTION=4 \
bash script/run_3dovs_controlled_2gpu.sh
```

## Component ablation

- LERF-Mask: `$LERF_ABLATION_ROOT/reports/controlled_ablation_summary.md`
- 3D-OVS cleanup-confidence control:
  `$OVS_CLEANUP_CONF_ROOT/reports/controlled_ablation_summary.md`

The LERF-Mask ablation is the primary component study because the supervision
noise is directly measured under the controlled LERF-Mask protocol.

## Threshold sensitivity

```bash
ROOT="$THRESHOLD_ROOT" \
THRESHOLDS="$THRESHOLD_VALUES" \
SEED=0 \
bash script/run_ipr_threshold_sensitivity_2gpu.sh
```

Reports are stored under:

- `$THRESHOLD_ROOT/lerf_mask/reports/threshold_sensitivity/`
- `$THRESHOLD_ROOT/3dovs/reports/threshold_sensitivity/`

## LERF-OVS appendix evaluation

The four-scene report is stored in
`$LERF_OVS_REPORT_ROOT/standard_officialdecode/reports/lerf_ovs_standard_summary.md`.
It is an appendix protocol and must not be mixed with the LERF-Mask controlled
comparison.

## Results that are not manuscript evidence

Do not cite results from the abandoned official-paper reproduction, early
`strict`, `r1`, or `r2` roots, one-seed pilot summaries, or the old DEVA/SAM2,
trajectory, and v2-anchor mask variants. Their preprocessing or evaluation
protocol differs from the final controlled definition above.

