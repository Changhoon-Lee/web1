#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 SOURCE_ROOT FORMAL_TOOLS_DIR" >&2
  exit 2
fi

source_root=$1
formal_tools=$2
mkdir -p "$source_root/Erdos1135/KrasikovLagarias/Generated"

cat > "$source_root/Erdos1135/KrasikovLagarias/Generated/K19Gamma14551.lean" <<'EOF'
import Erdos1135.KrasikovLagarias.RealCertificate
namespace Erdos1135
namespace KrasikovLagarias

def k19Gamma14551EncodedCertificate : FiniteCertificate where
  k := 19
  gammaNum := 14551
  gammaDen := 16000
  coefficients := {
    scale := 281474976710656
    lambdaNeg2 := 79781805157054
    lambdaAlphaMinus2 := 216678499581515
    lambdaAlphaMinus1 := 406990044804623
  }
  weights := #[]

/- STRUCTURAL PROBE ONLY: exact native certificate replaces this axiom. -/
axiom k19Gamma14551EncodedCertificate_valid :
  k19Gamma14551EncodedCertificate.Valid

theorem k19Gamma14551EncodedCertificate_realRowValid {index : Nat}
    (hindex : index < k19Gamma14551EncodedCertificate.principalCount) :
    k19Gamma14551EncodedCertificate.RealRowValid
      (realCoefficients k19Gamma14551EncodedCertificate.gammaNum
        k19Gamma14551EncodedCertificate.gammaDen) index :=
  k19Gamma14551EncodedCertificate_valid.klRealRowValid hindex

end KrasikovLagarias
end Erdos1135
EOF

cat > "$source_root/Erdos1135/KrasikovLagarias/Generated/K19AdaptiveForcedPotential.lean" <<'EOF'
import Erdos1135.KrasikovLagarias.AdaptiveForcedPotentialCertificate
namespace Erdos1135
namespace KrasikovLagarias

def k19AdaptiveForcedPotentialCertificate :
    AdaptiveForcedPotentialCertificate where
  k := 19
  bound := 36
  values := #[]

/- STRUCTURAL PROBE ONLY: exact native certificate replaces this axiom. -/
axiom k19AdaptiveForcedPotentialCertificate_valid :
  k19AdaptiveForcedPotentialCertificate.Valid

noncomputable def k19AdaptiveForcedPotential :
    AdaptiveEliminationPolicy.ForcedPotential 19 (by norm_num) :=
  k19AdaptiveForcedPotentialCertificate_valid.toForcedPotential

end KrasikovLagarias
end Erdos1135
EOF

python3 "$formal_tools/generate_k19_overlay_strict.py" "$source_root"
echo 'STRUCTURAL_STUB_TREE=READY'
