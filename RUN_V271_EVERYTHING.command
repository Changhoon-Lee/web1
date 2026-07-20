#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
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
python -m unittest discover -s tests -v
rm -rf v271_results runtime data/deribit_public
python -m src.v271_cli all --root "$ROOT" --years "${V271_YEARS:-6}"
python -m src.v271_cli verify --root "$ROOT"
echo "FINAL ZIP: $ROOT/runtime/V27_1_Open_Free_Deribit_Handoff.zip"
