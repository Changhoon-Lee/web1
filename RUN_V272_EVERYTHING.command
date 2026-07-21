#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-v272.txt
export PYTHONPATH="$(pwd)/src"
python scripts/run_v272_authority_tests.py
python src/v272_cli.py all --data data/v272_free_chain --output v272_results --handoff runtime/V272_Actual_Inverse_Handoff.zip --record-minutes 0
python src/v272_cli.py verify --output v272_results
printf '\nV27.2 completed:\n%s\n' "$(pwd)/runtime/V272_Actual_Inverse_Handoff.zip"
