#!/bin/bash
set -uo pipefail

V272_HOME="${V272_HOME:-$HOME/Library/Application Support/V272Free}"
DATA_DIR="$V272_HOME/data/v272_free_chain"
RESULTS_DIR="$V272_HOME/v272_results"
RUNTIME_DIR="$V272_HOME/runtime"
LOG_DIR="$HOME/Library/Logs/V272Free"
HASH_STATE="$V272_HOME/.last_verified_input_hash"
DATE_STATE="$V272_HOME/.last_verified_utc_date"
RECORDER_LOG="$LOG_DIR/recorder.log"
AUDIT_LOG="$LOG_DIR/audit.log"

mkdir -p "$DATA_DIR" "$RESULTS_DIR" "$RUNTIME_DIR" "$LOG_DIR"
source "$V272_HOME/.venv/bin/activate"
export PYTHONPATH="$V272_HOME/src"

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$RECORDER_LOG"; }
log "V27.2 safe launcher start"

while true; do
  python "$V272_HOME/src/v272_cli.py" record --data "$DATA_DIR" --record-minutes 0 >> "$RECORDER_LOG" 2>&1

  READY=$(python "$V272_HOME/src/v272_cli.py" audit --data "$DATA_DIR" 2>> "$RECORDER_LOG" | python -c '
import json,sys
try: print(json.load(sys.stdin)["coverage"]["ready"])
except Exception as exc:
    print(f"coverage parse failure: {exc}", file=sys.stderr)
    print(False)
' 2>> "$RECORDER_LOG")

  if [ "$READY" = "True" ]; then
    TODAY_UTC=$(date -u +%Y-%m-%d)
    LAST_DATE=""; [ -f "$DATE_STATE" ] && LAST_DATE=$(cat "$DATE_STATE")
    if [ "$TODAY_UTC" != "$LAST_DATE" ]; then
      CURRENT_HASH=$(python -c "
import sys
from pathlib import Path
sys.path.insert(0, '$V272_HOME/src')
from v272_free import input_manifest
print(input_manifest(Path('$DATA_DIR'))['tree_sha256'])
" 2>> "$RECORDER_LOG")
      LAST_HASH=""; [ -f "$HASH_STATE" ] && LAST_HASH=$(cat "$HASH_STATE")
      if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
        log "ready=True; running verified daily audit hash=$CURRENT_HASH"
        if python "$V272_HOME/src/v272_cli.py" all \
             --data "$DATA_DIR" --output "$RESULTS_DIR" \
             --handoff "$RUNTIME_DIR/V272_Actual_Inverse_Handoff.zip" \
             --no-record --record-minutes 0 >> "$AUDIT_LOG" 2>&1 \
           && python "$V272_HOME/src/v272_cli.py" verify --output "$RESULTS_DIR" >> "$AUDIT_LOG" 2>&1
        then
          printf '%s\n' "$CURRENT_HASH" > "$HASH_STATE.tmp" && mv "$HASH_STATE.tmp" "$HASH_STATE"
          printf '%s\n' "$TODAY_UTC" > "$DATE_STATE.tmp" && mv "$DATE_STATE.tmp" "$DATE_STATE"
          log "audit verified and committed"
        else
          log "audit failed; state not committed"
        fi
      fi
    fi
  fi

  NOW=$(date +%s)
  NEXT=$(( (NOW / 300 + 1) * 300 ))
  SLEEP=$(( NEXT - NOW ))
  [ "$SLEEP" -gt 0 ] && sleep "$SLEEP"
done
