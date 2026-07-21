#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V272_HOME="$HOME/Library/Application Support/V272Free"
LOG_DIR="$HOME/Library/Logs/V272Free"
PLIST="$HOME/Library/LaunchAgents/com.zcode.v272free.recorder.plist"
mkdir -p "$V272_HOME/src" "$V272_HOME/tests" "$V272_HOME/scripts" "$LOG_DIR" "$HOME/Library/LaunchAgents"
cp src/v272_core.py src/v272_core_legacy.py src/v272_free.py src/v272_cli.py "$V272_HOME/src/"
cp tests/test_v272.py tests/test_v272_wrapper.py "$V272_HOME/tests/"
cp scripts/run_v272_authority_tests.py "$V272_HOME/scripts/"
cp requirements-v272.txt V272_SAFE_LAUNCHER.sh V272_PROTOCOL.json V272_README.md "$V272_HOME/"
chmod +x "$V272_HOME/V272_SAFE_LAUNCHER.sh" "$V272_HOME/scripts/run_v272_authority_tests.py"
python3 -m venv "$V272_HOME/.venv"
source "$V272_HOME/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$V272_HOME/requirements-v272.txt"
export PYTHONPATH="$V272_HOME/src"
python "$V272_HOME/scripts/run_v272_authority_tests.py"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.zcode.v272free.recorder</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$V272_HOME/V272_SAFE_LAUNCHER.sh</string></array>
  <key>WorkingDirectory</key><string>$V272_HOME</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/launchd.stdout.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/launchd.stderr.log</string>
</dict></plist>
PLIST
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/com.zcode.v272free.recorder"
printf 'Installed and started V27.2 at:\n%s\n' "$V272_HOME"
