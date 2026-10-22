# Final script map

Only maintained experiment and figure entry points are kept in this directory.

## Preprocessing

- `prepare_ipr_strict_protocol.sh`: final LERF-Mask IPR preprocessing.
- `prepare_3dovs_ipr_consistency.sh`: final 3D-OVS IPR preprocessing.
- `prepare_3dovs_language_features.sh`: 3D-OVS language-feature preparation.
- `subset_ipr_training_views.py`: restrict masks to training views.
- `build_query_file_from_masks.py`: build evaluation query manifests.

## Training and evaluation

- `run_ipr_strict_protocol_2gpu.sh`: LERF-Mask baseline/IPR training.
- `eval_ipr_strict_protocol_2gpu.sh`: LERF-Mask evaluation.
- `run_3dovs_controlled_2gpu.sh`: 3D-OVS baseline/IPR training.
- `eval_3dovs_controlled_2gpu.sh`: 3D-OVS evaluation.
- `summarize_controlled_ipr_ablation.py`: aggregate multi-seed metrics.

## Ablation and sensitivity

- `prepare_lerf_mask_ipr_consistency_ablation.sh`
- `run_lerf_mask_consistency_ablation_2gpu.sh`
- `audit_ipr_ablation_inputs.py`
- `prepare_ipr_threshold_sensitivity.sh`
- `run_ipr_threshold_sensitivity_2gpu.sh`
- `summarize_ipr_threshold_sensitivity.py`

## LERF-OVS appendix

- `audit_lerf_ovs_reuse.py`
- `eval_lerf_ovs_standard.py`
- `eval_lerf_ovs_standard_2gpu.sh`
- `summarize_lerf_ovs_standard.py`
- `merge_lerf_ovs_baselines.py`
- `build_lerf_ovs_comparison.sh`

## Publication figures

- `export_real_main_figure_assets.py`
- `export_ipr_method_assets.py`
- `export_ipr_noise_examples.py`
- `generate_paper_experiment_figures.py`

Canonical scenes, seeds, thresholds, paths, and variant names are defined in
`config/experiments/paper_final.env`.
