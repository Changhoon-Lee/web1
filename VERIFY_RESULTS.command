#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python src/v24_cli.py verify --output results
python src/v24_cli.py handoff --output results --destination runtime/V24_ZCode_Handoff.zip
python - <<'PY'
from pathlib import Path
from v24_core import sha256_file
p=Path('runtime/V24_ZCode_Handoff.zip')
print({'path': str(p.resolve()), 'size': p.stat().st_size, 'sha256': sha256_file(p)})
PY
