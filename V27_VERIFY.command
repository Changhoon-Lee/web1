#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python src/v27_cli.py verify --output v27_results
python src/v27_cli.py handoff --output v27_results --destination runtime/V27_Deribit_Long_Gamma_Handoff.zip
python - <<'PY'
from pathlib import Path
from v27_core import sha256_file
p = Path('runtime/V27_Deribit_Long_Gamma_Handoff.zip')
print({'path': str(p.resolve()), 'size': p.stat().st_size, 'sha256': sha256_file(p)})
PY
