#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3.13 || command -v python3)}"
[ -d .venv ] || "$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python - <<'PY'
import numpy,pandas,pytest,sys
print({'python':sys.version,'numpy':numpy.__version__,'pandas':pandas.__version__,'pytest':pytest.__version__})
PY
