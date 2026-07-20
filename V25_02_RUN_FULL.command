#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
ARGS=(all --output v25_results --handoff runtime/V25_Dual_Causal_Defense_Handoff.zip)
if [ -n "${V25_ENGINE_RETURNS_FILE:-}" ]; then ARGS+=(--input "$V25_ENGINE_RETURNS_FILE"); fi
if [ -n "${TAIL_PROVENANCE_FILE:-}" ]; then ARGS+=(--provenance "$TAIL_PROVENANCE_FILE"); fi
python src/v25_cli.py "${ARGS[@]}"
