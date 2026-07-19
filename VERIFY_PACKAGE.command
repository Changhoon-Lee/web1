#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
./01_RUN_TESTS.command
source .venv/bin/activate
if [ -d results ]; then python src/v23_final_lab.py verify --output results; fi
python - <<'PY'
import json,hashlib,pathlib
p=pathlib.Path('PROTOCOL.json')
print({'protocol_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'version':json.loads(p.read_text())['version']})
PY
