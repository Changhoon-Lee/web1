#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -p 'test_*.py' -v
