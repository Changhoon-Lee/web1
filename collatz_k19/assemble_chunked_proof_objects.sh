#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 SOURCE_ROOT SOURCE_ROW_ARTIFACTS ADAPTIVE_ROW_ARTIFACTS" >&2
  exit 2
fi

source_root=$1
source_artifacts=$2
adaptive_artifacts=$3
base_dir="$source_root/.lake/build/lib/lean/Erdos1135/KrasikovLagarias"
olean_dir="$base_dir/Generated"
generated_src="$source_root/Erdos1135/KrasikovLagarias/Generated"
mkdir -p "$olean_dir"

check_dependency_hashes() {
  local artifact_root=$1
  local module=$2
  local directory=$3
  local expected_count=${4:-8}
  local actual
  actual=$(sha256sum "$directory/$module.olean" | awk '{print $1}')
  mapfile -t files < <(find "$artifact_root" -name "$module.??.sha256" -type f | sort)
  [[ ${#files[@]} -eq $expected_count ]]
  for file in "${files[@]}"; do
    [[ $(cat "$file") == "$actual" ]]
  done
  printf '%s=%s\n' "${module}_OLEAN_SHA256" "$actual"
}

# Every row proof object must have been compiled against byte-identical common
# semantics and generated Data/Metadata boundaries.  Hash all four dependencies
# on each side before accepting any interval `.olean`.
check_dependency_hashes "$source_artifacts" StreamingCertificate "$base_dir"
check_dependency_hashes "$source_artifacts" ChunkedStreamingCertificate "$base_dir"
check_dependency_hashes "$source_artifacts" K19Gamma14551Data "$olean_dir"
check_dependency_hashes "$source_artifacts" K19Gamma14551Metadata "$olean_dir"

check_dependency_hashes "$adaptive_artifacts" StreamingCertificate "$base_dir"
check_dependency_hashes "$adaptive_artifacts" ChunkedStreamingCertificate "$base_dir"
check_dependency_hashes "$adaptive_artifacts" K19AdaptiveForcedPotentialData "$olean_dir"
check_dependency_hashes "$adaptive_artifacts" K19AdaptiveForcedPotentialMetadata "$olean_dir"

mapfile -t source_oleans < <(
  find "$source_artifacts" -name 'K19Gamma14551Rows??.olean' -type f | sort
)
mapfile -t adaptive_oleans < <(
  find "$adaptive_artifacts" -name 'K19AdaptiveForcedPotentialRows??.olean' -type f | sort
)
[[ ${#source_oleans[@]} -eq 8 ]]
[[ ${#adaptive_oleans[@]} -eq 8 ]]

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
#print axioms Erdos1135.KrasikovLagarias.k19Gamma14551EncodedCertificate_realRowValid
#print axioms Erdos1135.KrasikovLagarias.k19AdaptiveForcedPotentialCertificate_valid
EOF

"${lake_env[@]}" "$source_root/K19ChunkedAssetAxiomAudit.lean" \
  2>&1 | tee "$source_root/K19ChunkedAssetAxiomAudit.out"
if grep -q 'sorryAx' "$source_root/K19ChunkedAssetAxiomAudit.out"; then
  echo 'CHUNKED_ASSET_AXIOM_AUDIT=FAIL_SORRYAX' >&2
  exit 5
fi

echo 'SOURCE_ROW_PROOF_OBJECTS=8_AUTHENTICATED'
echo 'ADAPTIVE_ROW_PROOF_OBJECTS=8_AUTHENTICATED'
echo 'SOURCE_DATA_METADATA_DEPENDENCIES=AUTHENTICATED'
echo 'ADAPTIVE_DATA_METADATA_DEPENDENCIES=AUTHENTICATED'
echo 'STREAMING_SEMANTICS_DEPENDENCIES=AUTHENTICATED'
echo 'CHUNKED_ASSET_AXIOM_AUDIT=PASS_NO_SORRYAX'
echo 'CHUNKED_PROOF_OBJECT_ASSEMBLY=PASS'
