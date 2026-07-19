#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || ./00_INSTALL.command
source .venv/bin/activate
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
SAMPLES="${V23_BOOTSTRAP_SAMPLES:-20000}"
ARGS=(run --root . --output results --bootstrap-samples "$SAMPLES" --prior-trials "${V23_PRIOR_TRIALS:-35000}")
if [ -n "${ENGINE_RETURNS_FILE:-}" ]; then ARGS+=(--input "$ENGINE_RETURNS_FILE"); fi
python src/v23_final_lab.py "${ARGS[@]}"
python src/v23_final_lab.py verify --output results
open results/FINAL_REPORT.md 2>/dev/null || true
