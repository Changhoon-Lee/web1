#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then "$PYTHON_BIN" -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./V25_01_RUN_TESTS.command
./V25_02_RUN_FULL.command
./V25_VERIFY_RESULTS.command
printf '\nV25 completed. Final handoff:\n%s\n' "$(pwd)/runtime/V25_Dual_Causal_Defense_Handoff.zip"
if command -v open >/dev/null 2>&1; then open "$(pwd)/runtime"; fi
