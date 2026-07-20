#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
source .venv/bin/activate
python -m src.v271_cli record --root "$ROOT" --record-minutes "${V271_RECORD_MINUTES:-1440}" --snapshot-seconds "${V271_SNAPSHOT_SECONDS:-30}"
