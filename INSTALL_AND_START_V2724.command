#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

V2724_HOME="$HOME/Library/Application Support/V2724Free"
OLD_HOME="$HOME/Library/Application Support/V272Free"
LOG_DIR="$HOME/Library/Logs/V2724Free"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
NEW_PLIST="$LAUNCH_DIR/com.zcode.v2724free.recorder.plist"
OLD_PLIST="$LAUNCH_DIR/com.zcode.v272free.recorder.plist"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_ROOT="$V2724_HOME/legacy_v2723_control/$STAMP"

mkdir -p "$V2724_HOME/src" "$V2724_HOME/tests" "$V2724_HOME/scripts" \
  "$V2724_HOME/data/v2724_ws_chain" "$V2724_HOME/runtime" "$LOG_DIR" "$LAUNCH_DIR"

# Stop the diagnostic REST recorder. Preserve its code, data, logs, and plist;
# never mix them into the V27.2.4 authority clock.
launchctl bootout "gui/$(id -u)" "$OLD_PLIST" 2>/dev/null || true
if [ -e "$OLD_HOME" ] || [ -e "$OLD_PLIST" ]; then
  mkdir -p "$BACKUP_ROOT"
  if [ -e "$OLD_HOME" ]; then
    mv "$OLD_HOME" "$BACKUP_ROOT/V272Free"
  fi
  if [ -e "$OLD_PLIST" ]; then
    mv "$OLD_PLIST" "$BACKUP_ROOT/com.zcode.v272free.recorder.plist"
  fi
fi

# Stop an older V27.2.4 process before replacing code. Existing V27.2.4
# authority data remains in place and is not reset on reinstall.
launchctl bootout "gui/$(id -u)" "$NEW_PLIST" 2>/dev/null || true

# v272_free.py and v272_cli.py are copied only so the frozen V27.2 accounting
# regression tests can run. The LaunchAgent never executes them.
cp src/v272_core.py src/v272_core_legacy.py src/v272_free.py src/v272_cli.py \
  src/v2724_ws.py src/v2724_cli.py "$V2724_HOME/src/"
cp tests/test_v272.py tests/test_v272_wrapper.py tests/test_v2724_ws.py "$V2724_HOME/tests/"
cp scripts/run_v2724_authority_tests.py "$V2724_HOME/scripts/"
cp requirements-v2724.txt V2724_PROTOCOL.json V2724_README.md V2724_SAFE_LAUNCHER.sh "$V2724_HOME/"
chmod +x "$V2724_HOME/V2724_SAFE_LAUNCHER.sh" "$V2724_HOME/scripts/run_v2724_authority_tests.py"

python3 -m venv "$V2724_HOME/.venv"
source "$V2724_HOME/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$V2724_HOME/requirements-v2724.txt"
export PYTHONPATH="$V2724_HOME/src"
python "$V2724_HOME/scripts/run_v2724_authority_tests.py"

cat > "$NEW_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.zcode.v2724free.recorder</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string>
    <string>$V2724_HOME/V2724_SAFE_LAUNCHER.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$V2724_HOME</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$LOG_DIR/launchd.stdout.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/launchd.stderr.log</string>
</dict></plist>
PLIST

launchctl bootstrap "gui/$(id -u)" "$NEW_PLIST"
launchctl kickstart -k "gui/$(id -u)/com.zcode.v2724free.recorder"

printf '\nV27.2.4 installed and started.\n'
printf 'HOME: %s\n' "$V2724_HOME"
printf 'DATA: %s\n' "$V2724_HOME/data/v2724_ws_chain"
printf 'LOGS: %s\n' "$LOG_DIR"
printf 'LAUNCHAGENT: com.zcode.v2724free.recorder\n'
printf 'LEGACY V27.2.3 BACKUP: %s\n' "$BACKUP_ROOT"
