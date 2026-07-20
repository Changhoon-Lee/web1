#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python src/v27_tardis.py
