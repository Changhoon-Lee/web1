#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-v2724.txt
export PYTHONPATH="$(pwd)/src"
python scripts/run_v2724_authority_tests.py
rm -rf data/v2724_ws_chain v2724_results runtime
mkdir -p data/v2724_ws_chain
python src/v2724_cli.py all \
  --data data/v2724_ws_chain \
  --output v2724_results \
  --handoff runtime/V2724_WebSocket_Authority_Handoff.zip
python src/v2724_cli.py verify --output v2724_results
printf '\nV27.2.4 fail-closed verification completed.\n%s\n' "$(pwd)/runtime/V2724_WebSocket_Authority_Handoff.zip"
