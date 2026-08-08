#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 SOURCE_ROOT SOURCE_ROW_ARTIFACTS ADAPTIVE_ROW_ARTIFACTS" >&2
  exit 2
fi

source_root=$1
source_artifacts=$2
adaptive_artifacts=$3
olean_dir="$source_root/.lake/build/lib/lean/Erdos1135/KrasikovLagarias/Generated"
generated_src="$source_root/Erdos1135/KrasikovLagarias/Generated"
mkdir -p "$olean_dir"

source_data="$olean_dir/K19Gamma14551Data.olean"
adaptive_data="$olean_dir/K19AdaptiveForcedPotentialData.olean"
test -s "$source_data"
test -s "$adaptive_data"
source_hash=$(sha256sum "$source_data" | awk '{print $1}')
adaptive_hash=$(sha256sum "$adaptive_data" | awk '{print $1}')

mapfile -t source_hash_files < <(find "$source_artifacts" -name 'data.*.sha256' -type f | sort)
mapfile -t source_oleans < <(find "$source_artifacts" -name 'K19Gamma14551Rows??.olean' -type f | sort)
mapfile -t adaptive_hash_files < <(find "$adaptive_artifacts" -name 'data.*.sha256' -type f | sort)
mapfile -t adaptive_oleans < <(find "$adaptive_artifacts" -name 'K19AdaptiveForcedPotentialRows??.olean' -type f | sort)

[[ ${#source_hash_files[@]} -eq 8 ]]
[[ ${#source_oleans[@]} -eq 8 ]]
[[ ${#adaptive_hash_files[@]} -eq 8 ]]
[[ ${#adaptive_oleans[@]} -eq 8 ]]

for file in "${source_hash_files[@]}"; do
  [[ $(cat "$file") == "$source_hash" ]]
done
for file in "${adaptive_hash_files[@]}"; do
  [[ $(cat "$file") == "$adaptive_hash" ]]
done

cp "${source_oleans[@]}" "$olean_dir/"
cp "${adaptive_oleans[@]}" "$olean_dir/"

# Prevent Lake from scheduling any native interval again.  The authenticated
# `.olean` objects above remain available on LEAN_PATH as compiled imports.
rm -f "$generated_src"/K19Gamma14551Rows??.lean
rm -f "$generated_src"/K19AdaptiveForcedPotentialRows??.lean

lake_env=(lake env lean)
"${lake_env[@]}" "$generated_src/K19Gamma14551.lean" \
  -o "$olean_dir/K19Gamma14551.olean" \
  -i "$olean_dir/K19Gamma14551.ilean"
"${lake_env[@]}" "$generated_src/K19AdaptiveForcedPotential.lean" \
  -o "$olean_dir/K19AdaptiveForcedPotential.olean" \
  -i "$olean_dir/K19AdaptiveForcedPotential.ilean"

cat > "$source_root/K19ChunkedAssetAxiomAudit.lean" <<'EOF'
import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551
import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotential
#print axioms Erdos1135.KrasikovLagarias.k19Gamma14551EncodedCertificate_valid
#print axioms Erdos1135.KrasikovLagarias.k19AdaptiveForcedPotentialCertificate_valid
EOF

"${lake_env[@]}" "$source_root/K19ChunkedAssetAxiomAudit.lean" \
  2>&1 | tee "$source_root/K19ChunkedAssetAxiomAudit.out"
if grep -q 'sorryAx' "$source_root/K19ChunkedAssetAxiomAudit.out"; then
  echo 'CHUNKED_ASSET_AXIOM_AUDIT=FAIL_SORRYAX' >&2
  exit 5
fi

echo "SOURCE_DATA_OLEAN_SHA256=$source_hash"
echo "ADAPTIVE_DATA_OLEAN_SHA256=$adaptive_hash"
echo 'SOURCE_ROW_PROOF_OBJECTS=8_AUTHENTICATED'
echo 'ADAPTIVE_ROW_PROOF_OBJECTS=8_AUTHENTICATED'
echo 'CHUNKED_ASSET_AXIOM_AUDIT=PASS_NO_SORRYAX'
echo 'CHUNKED_PROOF_OBJECT_ASSEMBLY=PASS'
