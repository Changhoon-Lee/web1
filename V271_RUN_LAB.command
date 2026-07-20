#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source .venv/bin/activate
python -m src.v271_cli run --root "$ROOT"
