#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
python src/v27_free_open.py audit --data data/v27_free_chain
if [ -d v27_free_results ]; then
  python src/v27_free_verify.py --output v27_free_results
fi
