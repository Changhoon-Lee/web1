#!/bin/bash
set -euo pipefail

V2724_HOME="${V2724_HOME:-$HOME/Library/Application Support/V2724Free}"
DATA_DIR="$V2724_HOME/data/v2724_ws_chain"
OUTPUT_DIR="$V2724_HOME/v2724_results"
HANDOFF="$V2724_HOME/runtime/V2724_WebSocket_Authority_Handoff.zip"
LOG_DIR="$HOME/Library/Logs/V2724Free"

mkdir -p "$DATA_DIR" "$OUTPUT_DIR" "$V2724_HOME/runtime" "$LOG_DIR"
source "$V2724_HOME/.venv/bin/activate"
export PYTHONPATH="$V2724_HOME/src"
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

exec python "$V2724_HOME/src/v2724_cli.py" record \
  --data "$DATA_DIR" \
  --output "$OUTPUT_DIR" \
  --handoff "$HANDOFF"
