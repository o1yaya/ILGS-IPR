# ILGS-IPR

Research code for **Identity-Preserving Reliability (IPR)** on top of the
released Identity-aware Language Gaussian Splatting (ILGS) implementation.
IPR estimates query-free reliability from training-view identity tracks and
uses the resulting pixel confidence map to reweight only the 2D identity loss.
The Gaussian representation, language branch, and text-query inference path
remain unchanged.

This is a modified research repository, not an unmodified copy of the official
ILGS release. The implementation boundary and verified results are documented
in [IPR_CODE_CHANGES_AND_RESULTS.md](documents/IPR_CODE_CHANGES_AND_RESULTS.md).

## Repository layout

| Path | Purpose |
|---|---|
| `train.py` | Controlled ILGS training with optional IPR confidence maps |
| `refine_object_masks.py` | Training-view mask cleanup and base confidence |
| `refine_object_masks_semantic_area.py` | Cross-view consistency and area-risk weighting |
| `arguments/`, `scene/`, `gaussian_renderer/`, `utils/` | ILGS/3DGS core implementation |
| `script/` | Final preprocessing, training, evaluation, ablation, and figure entry points |
| `config/experiments/paper_final.env` | Portable experiment defaults |
| `tests/` | Protocol and evaluation regression tests |

Datasets, checkpoints, model outputs, and generated figures are intentionally
excluded from Git.

## Installation

Follow [Installation.md](documents/Installation.md), then place the required
assets under:

```text
dataset/lerf/<scene>/
dataset/3dovs/<scene>/
checkpoints/open_clip_pytorch_model.bin
checkpoints/sam_vit_h_4b8939.pth
autoencoder/ckpt/<dataset>/<scene>/best_ckpt.pth
```

Dataset layout and the original ILGS preprocessing steps are described in
[Download.md](documents/Download.md) and
[Implementation.md](documents/Implementation.md).

## Quick start

Run commands from the repository root in the `ILGS` Conda environment:

```bash
conda activate ILGS
set -a
source config/experiments/paper_final.env
set +a
```

Prepare query-free IPR supervision:

```bash
DATASET_ROOT="$LERF_DATASET_ROOT" SCENES="$LERF_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_ipr_strict_protocol.sh

DATASET_ROOT="$OVS_DATASET_ROOT" SCENES="$OVS_SCENES" \
CONSISTENCY_THRESHOLD="$IPR_THRESHOLD" \
bash script/prepare_3dovs_ipr_consistency.sh
```

Train the final variants:

```bash
EXTERNAL_ROOT="$LERF_MAIN_ROOT" DATASET_ROOT="$LERF_DATASET_ROOT" \
SCENES="$LERF_SCENES" VARIANTS="$LERF_VARIANT" SEEDS="$LERF_SEEDS" \
RESOLUTION=1 bash script/run_ipr_strict_protocol_2gpu.sh

EXTERNAL_ROOT="$OVS_MAIN_ROOT" DATASET_ROOT="$OVS_DATASET_ROOT" \
SCENES="$OVS_SCENES" VARIANTS="$OVS_VARIANT" SEEDS="$OVS_SEEDS" \
RESOLUTION=4 bash script/run_3dovs_controlled_2gpu.sh
```

See [EXPERIMENTS_FINAL.md](documents/EXPERIMENTS_FINAL.md) for evaluation,
component ablation, threshold sensitivity, and LERF-OVS appendix commands.

## Tests

```bash
python -m unittest tests.test_ipr_protocol_tools -v
```

## Upstream project

This work builds on the official ILGS code and paper:

> SungMin Jang and Wonjun Kim. Identity-aware Language Gaussian Splatting for
> Open-vocabulary 3D Semantic Segmentation. ICCV, 2025.

```bibtex
@inproceedings{jsmbankILGS,
  title={Identity-aware Language Gaussian Splatting for Open-vocabulary 3D Semantic Segmentation},
  author={SungMin Jang and Wonjun Kim},
  booktitle={Proceedings of the International Conference on Computer Vision},
  year={2025}
}
```

## License

Original ILGS code is distributed under Apache License 2.0. Components derived
from Gaussian Splatting remain subject to the Inria/MPII non-commercial
research license. See [LICENSE](LICENSE) and
[LICENSE_GAUSSIAN_SPLATTING.md](LICENSE_GAUSSIAN_SPLATTING.md).
