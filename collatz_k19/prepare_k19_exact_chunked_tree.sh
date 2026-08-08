#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 SOURCE_ROOT FORMAL_TOOLS_DIR REPLAY_DIR" >&2
  exit 2
fi

source_root=$1
formal_tools=$2
replay=$3
repo_root=$(cd "$(dirname "$0")/.." && pwd)

weights="$replay/k19_gamma14551_16000.u32le"
potential="$replay/k19_adaptive_potential.u8"
test -s "$weights"
test -s "$potential"

cp "$repo_root/collatz_k19/StreamingCertificate.lean" \
  "$source_root/Erdos1135/KrasikovLagarias/StreamingCertificate.lean"
cp "$repo_root/collatz_k19/ChunkedStreamingCertificate.lean" \
  "$source_root/Erdos1135/KrasikovLagarias/ChunkedStreamingCertificate.lean"

python3 "$formal_tools/generate_hex_artifacts.py" \
  "$weights" "$source_root/artifacts/kl_predecessor/k19_g14551_16000" \
  --chunk-bytes 33554432
python3 "$formal_tools/generate_hex_artifacts.py" \
  "$potential" "$source_root/artifacts/kl_predecessor/k19_adaptive_potential" \
  --chunk-bytes 33554432

python3 "$repo_root/collatz_k19/generate_k19_source_chunked.py" \
  "$source_root" --row-chunks 8
python3 "$repo_root/collatz_k19/generate_k19_adaptive_chunked.py" \
  "$source_root" --row-chunks 8
python3 "$formal_tools/generate_k19_overlay_strict.py" "$source_root"

cat >> "$source_root/lakefile.toml" <<'EOF'

[[lean_lib]]
name = "CollatzPredecessorK19"

[[lean_lib]]
name = "K19AxiomAudit"
EOF

echo 'K19_EXACT_CHUNKED_TREE=READY'
