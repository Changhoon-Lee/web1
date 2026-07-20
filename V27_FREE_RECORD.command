#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  source .venv/bin/activate
fi
export V27_FREE_RECORD_MINUTES="${V27_FREE_RECORD_MINUTES:-60}"
export V27_FREE_INTERVAL_SECONDS="${V27_FREE_INTERVAL_SECONDS:-300}"
python src/v27_free_open.py record --data data/v27_free_chain
python src/v27_free_open.py audit --data data/v27_free_chain
