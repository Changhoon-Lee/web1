#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m unittest discover -s tests -p 'test_v27*.py' -v

export V27_FREE_RECORD_MINUTES="${V27_FREE_RECORD_MINUTES:-1}"
export V27_FREE_INTERVAL_SECONDS="${V27_FREE_INTERVAL_SECONDS:-300}"
python src/v27_free_open.py all \
  --data data/v27_free_chain \
  --output v27_free_results \
  --handoff runtime/V27_Free_Open_Data_Only_Handoff.zip
python src/v27_free_verify.py --output v27_free_results

printf '\nFinal handoff:\n%s\n' "$(pwd)/runtime/V27_Free_Open_Data_Only_Handoff.zip"
