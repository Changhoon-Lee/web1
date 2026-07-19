#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"

ARGS=(all --output results --handoff runtime/V24_ZCode_Handoff.zip)
if [ -n "${ENGINE_RETURNS_FILE:-}" ]; then
  ARGS+=(--input "$ENGINE_RETURNS_FILE")
fi
python src/v24_cli.py "${ARGS[@]}"
