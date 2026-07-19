#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
./00_INSTALL.command
./01_RUN_TESTS.command
./02_RUN_FULL.command
./COLLECT_ZCODE_HANDOFF.command
printf '\nCompleted: results/FINAL_REPORT.md and runtime/V23_1_ZCode_Handoff.zip\n'
