#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-v27.txt

./V27_RUN_TESTS.command
./V27_RUN_FULL.command
./V27_VERIFY.command

printf '\nV27 completed. Final handoff:\n%s\n' "$(pwd)/runtime/V27_Deribit_Long_Gamma_Handoff.zip"
if command -v open >/dev/null 2>&1; then
  open "$(pwd)/runtime"
fi
