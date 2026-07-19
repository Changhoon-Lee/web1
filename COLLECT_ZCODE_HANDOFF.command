#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
python src/v23_final_lab.py package --root . --output runtime/V23_1_ZCode_Handoff.zip
open runtime 2>/dev/null || true
