#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
./01_RUN_TESTS.command
source .venv/bin/activate
if [ -d results ]; then python src/v23_final_lab.py verify --output results; fi
python - <<'PY'
import json,hashlib,pathlib
root=pathlib.Path('.')
protocol=root/'PROTOCOL.json'
print({'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),'protocol':json.loads(protocol.read_text())['version']})
PY
