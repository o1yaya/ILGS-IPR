# Script map for the final IPR experiments

Only the scripts listed below are canonical manuscript entry points. Other
files in `script/` are figure builders, manuscript utilities, diagnostics, or
superseded development helpers and are not required for final training.

For the implementation boundary and verified improvements, see
`documents/IPR_CODE_CHANGES_AND_RESULTS.md`.

## Core preparation

- `prepare_ipr_strict_protocol.sh`: LERF-Mask train-view preprocessing.
- `prepare_3dovs_ipr_consistency.sh`: 3D-OVS train-view preprocessing.
- `subset_ipr_training_views.py`: materializes training-view masks.
- `build_query_file_from_masks.py`: creates the evaluation-query audit file.
- `audit_ipr_vocabulary.py`: checks vocabulary leakage.

## Main training and evaluation

- `run_ipr_strict_protocol_2gpu.sh`: LERF-Mask training.
- `eval_ipr_strict_protocol_2gpu.sh`: LERF-Mask evaluation.
- `run_3dovs_controlled_2gpu.sh`: 3D-OVS training.
- `eval_3dovs_controlled_2gpu.sh`: 3D-OVS evaluation.
- `summarize_controlled_ipr_ablation.py`: controlled-result aggregation.

## Ablation and sensitivity

- `prepare_lerf_mask_ipr_consistency_ablation.sh`
- `run_lerf_mask_consistency_ablation_2gpu.sh`
- `prepare_ipr_threshold_sensitivity.sh`
- `run_ipr_threshold_sensitivity_2gpu.sh`
- `summarize_ipr_threshold_sensitivity.py`

## Appendix and figures

- `eval_lerf_ovs_standard.py`
- `eval_lerf_ovs_standard_2gpu.sh`
- `summarize_lerf_ovs_standard.py`
- `export_real_main_figure_assets.py`
- `export_ipr_method_assets.py`
- `export_ipr_noise_examples.py`
- `generate_paper_experiment_figures.py`: creates final quantitative and success-only qualitative figures from saved CSV reports and real test outputs.

The canonical paths, scene lists, seeds, and thresholds are defined in
`config/experiments/paper_final.env`.

Both final preparation scripts default to the same query-free consistency
threshold (`0.75`) and accept `CONSISTENCY_THRESHOLD` as an explicit override.

