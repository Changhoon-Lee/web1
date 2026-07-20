#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python src/v25_cli.py verify --output v25_results
python src/v25_cli.py handoff --output v25_results --destination runtime/V25_Dual_Causal_Defense_Handoff.zip
python - <<'PY'
from pathlib import Path
from v25_core import sha256_file
p=Path('runtime/V25_Dual_Causal_Defense_Handoff.zip')
print({'path':str(p.resolve()),'size':p.stat().st_size,'sha256':sha256_file(p)})
PY
