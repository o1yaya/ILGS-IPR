#!/usr/bin/env bash
set -eo pipefail

# Server-side setup helper for AnyGrasp SDK.
# Run on server, not on the Windows client.

ANYGRASP_ROOT="${ANYGRASP_ROOT:-/media/cx/data/cxdata/anygrasp}"
ENV_NAME="${ENV_NAME:-anygrasp}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
CUDA_VERSION_HINT="${CUDA_VERSION_HINT:-11.8}"
MAX_JOBS="${MAX_JOBS:-8}"
TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.6}"

mkdir -p "${ANYGRASP_ROOT}"
cd "${ANYGRASP_ROOT}"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda not found. Please initialize conda first." >&2
  exit 1
fi

eval "$(conda shell.bash hook)"

if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  conda create -y -n "${ENV_NAME}" "python=${PYTHON_VERSION}"
fi

conda activate "${ENV_NAME}"

python -m pip install --upgrade pip wheel ninja
python -m pip install "setuptools<70"
python -m pip install "numpy==1.24.4"

if [[ "${CUDA_VERSION_HINT}" == "11.8" ]]; then
  conda install -y -c nvidia/label/cuda-11.8.0 \
    cuda-nvcc cuda-cudart cuda-cudart-dev libcusparse libcusparse-dev
fi

if ! python - <<'PY' >/dev/null 2>&1
import torch
print(torch.__version__)
PY
then
  if [[ "${CUDA_VERSION_HINT}" == 11.* ]]; then
    python -m pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 \
      --index-url https://download.pytorch.org/whl/cu118
  else
    echo "[ERROR] Unsupported CUDA_VERSION_HINT=${CUDA_VERSION_HINT}; install PyTorch manually, then rerun." >&2
    exit 1
  fi
fi

python - <<'PY'
import torch
print("[torch]", torch.__version__, "cuda:", torch.version.cuda, "available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("[gpu]", torch.cuda.get_device_name(0))
else:
    raise SystemExit("[ERROR] CUDA is unavailable; refusing to build a CPU-only MinkowskiEngine")
PY

if [[ ! -d anygrasp_sdk ]]; then
  git clone https://github.com/graspnet/anygrasp_sdk.git
fi

cd anygrasp_sdk
if [[ -d .git ]]; then
  git pull --ff-only || true
fi

conda install -y openblas-devel -c anaconda

if [[ -z "${CUDA_HOME:-}" ]]; then
  if command -v nvcc >/dev/null 2>&1; then
    CUDA_BIN="$(dirname "$(command -v nvcc)")"
    export CUDA_HOME="$(dirname "${CUDA_BIN}")"
  elif [[ -d /usr/local/cuda-11.8 ]]; then
    export CUDA_HOME=/usr/local/cuda-11.8
  elif [[ -d /usr/local/cuda ]]; then
    export CUDA_HOME=/usr/local/cuda
  else
    echo "[ERROR] Could not find CUDA_HOME/nvcc. Install CUDA toolkit or export CUDA_HOME first." >&2
    exit 1
  fi
fi

export PATH="${CUDA_HOME}/bin:${PATH}"
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH:-}"
export MAX_JOBS="${MAX_JOBS}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}"

echo "[CUDA_HOME] ${CUDA_HOME}"
echo "[TORCH_CUDA_ARCH_LIST] ${TORCH_CUDA_ARCH_LIST}"
nvcc --version || true

mkdir -p dependencies
cd dependencies

if [[ ! -d MinkowskiEngine ]]; then
  if [[ -d "${ANYGRASP_ROOT}/MinkowskiEngine" ]]; then
    cp -a "${ANYGRASP_ROOT}/MinkowskiEngine" ./MinkowskiEngine
  else
    git clone https://github.com/chenxi-wang/MinkowskiEngine.git
  fi
fi

cd MinkowskiEngine
if [[ -d .git ]]; then
  git fetch --all --tags
fi

CUDA_MAJOR="$(python - <<'PY'
import torch
print((torch.version.cuda or "0.0").split(".")[0])
PY
)"

if [[ "${CUDA_MAJOR}" == "12" ]]; then
  [[ -d .git ]] && git checkout cuda-12-1
elif [[ "${CUDA_MAJOR}" == "13" ]]; then
  [[ -d .git ]] && git checkout cuda-13
else
  [[ -d .git ]] && git checkout master
fi

# CUDA 11.8's Thrust requires an explicit execution-policy include for
# thrust::device, which this older MinkowskiEngine header omits.
THRUST_HEADER="src/3rdparty/concurrent_unordered_map.cuh"
if ! grep -q '^#include <thrust/execution_policy.h>' "${THRUST_HEADER}"; then
  sed -i '/^#include <thrust\/count.h>$/a #include <thrust/execution_policy.h>' "${THRUST_HEADER}"
fi

COORDINATE_MAP_GPU="src/coordinate_map_gpu.cu"
if ! grep -q '^#include <thrust/remove.h>' "${COORDINATE_MAP_GPU}"; then
  sed -i '/^#include <thrust\/execution_policy.h>$/a #include <thrust/remove.h>' "${COORDINATE_MAP_GPU}"
fi
if ! grep -q '^#include <thrust/unique.h>' "${COORDINATE_MAP_GPU}"; then
  sed -i '/^#include <thrust\/remove.h>$/a #include <thrust/unique.h>' "${COORDINATE_MAP_GPU}"
fi

SPMM_GPU="src/spmm.cu"
if ! grep -q '^#include <thrust/execution_policy.h>' "${SPMM_GPU}"; then
  sed -i '/^#include <cusparse.h>$/a #include <thrust/execution_policy.h>' "${SPMM_GPU}"
fi
if ! grep -q '^#include <thrust/sort.h>' "${SPMM_GPU}"; then
  sed -i '/^#include <thrust\/execution_policy.h>$/a #include <thrust/sort.h>' "${SPMM_GPU}"
fi
if ! grep -q '^#include <thrust/reduce.h>' "${SPMM_GPU}"; then
  sed -i '/^#include <thrust\/sort.h>$/a #include <thrust/reduce.h>' "${SPMM_GPU}"
fi
if ! grep -q '^#include <thrust/iterator/zip_iterator.h>' "${SPMM_GPU}"; then
  sed -i '/^#include <thrust\/reduce.h>$/a #include <thrust/iterator/zip_iterator.h>' "${SPMM_GPU}"
fi
if ! grep -q '^#include <thrust/tuple.h>' "${SPMM_GPU}"; then
  sed -i '/^#include <thrust\/iterator\/zip_iterator.h>$/a #include <thrust/tuple.h>' "${SPMM_GPU}"
fi

python setup.py install \
  --force_cuda \
  --cuda_home="${CUDA_HOME}" \
  --blas_include_dirs="${CONDA_PREFIX}/include" \
  --blas_library_dirs="${CONDA_PREFIX}/lib" \
  --blas=openblas

cd "${ANYGRASP_ROOT}/anygrasp_sdk"
python -m pip install -r requirements.txt
python -m pip install "numpy==1.24.4"

cd pointnet2
python setup.py install

cd "${ANYGRASP_ROOT}"
if [[ ! -d graspnetAPI ]]; then
  git clone https://github.com/graspnet/graspnetAPI.git
fi
cd graspnetAPI
python -m pip install .

cd "${ANYGRASP_ROOT}/anygrasp_sdk/grasp_detection"
SOABI="$(python - <<'PY'
import sysconfig
print(sysconfig.get_config_var("SOABI"))
PY
)"

MATCHED_SO="$(ls gsnet_versions/gsnet.${SOABI}*.so 2>/dev/null | head -n 1 || true)"
if [[ -z "${MATCHED_SO}" ]]; then
  echo "[ERROR] No gsnet binary matching ${SOABI} under grasp_detection/gsnet_versions." >&2
  echo "Available files:" >&2
  ls gsnet_versions >&2
  exit 1
fi
cp "${MATCHED_SO}" gsnet.so

echo "[OK] copied ${MATCHED_SO} -> grasp_detection/gsnet.so"

python - <<'PY'
import MinkowskiEngine as ME
import graspnetAPI
from gsnet import get_feature_id
print("[MinkowskiEngine]", ME.__version__ if hasattr(ME, "__version__") else "import ok")
print("[graspnetAPI] import ok")
print("[AnyGrasp feature id]")
print(get_feature_id())
PY

cat <<TXT

Next required manual steps:
1. Copy the AnyGrasp feature id above.
2. Submit the official license form:
   https://forms.gle/XVV3Eip8njTYJEBo6
3. After receiving the license zip and detection checkpoint, put them here:
   ${ANYGRASP_ROOT}/anygrasp_sdk/grasp_detection/license
   ${ANYGRASP_ROOT}/anygrasp_sdk/grasp_detection/log/checkpoint_detection.tar
4. Then validate:
   cd ${ANYGRASP_ROOT}/anygrasp_sdk/grasp_detection
   conda activate anygrasp
   python -c "from gsnet import check_license; check_license('license')"

TXT
