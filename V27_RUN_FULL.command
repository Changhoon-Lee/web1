#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
ARGS=(all --output v27_results --compact data/v27_compact --handoff runtime/V27_Deribit_Long_Gamma_Handoff.zip)
if [ -n "${V27_OPTIONS_DATA_DIR:-}" ]; then
  ARGS+=(--input "$V27_OPTIONS_DATA_DIR")
fi
python src/v27_cli.py "${ARGS[@]}"
