#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
MINUTES="${V27_RECORD_MINUTES:-60}"
SNAPSHOT="${V27_RECORD_SNAPSHOT_MINUTES:-5}"
python src/v27_live_recorder.py --currency "${V27_CURRENCY:-BTC}" --minutes "$MINUTES" --snapshot-minutes "$SNAPSHOT"
