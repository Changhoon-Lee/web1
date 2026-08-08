#!/usr/bin/env python3
"""Generate the exact K19 source-LP wrapper with two formal decompositions.

Every hexadecimal payload fragment is elaborated in its own Lean module, which
keeps the 3.10 GB textual payload out of any single elaboration unit.  The
387,420,489 row obligations are independently split into consecutive native
intervals and recombined into the unchanged `FiniteCertificate.Valid` theorem.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TOTAL = 387_420_489


def split_counts(total: int, chunks: int) -> list[tuple[int, int]]:
    q, r = divmod(total, chunks)
    out: list[tuple[int, int]] = []
    start = 0
    for i in range(chunks):
        count = q + (1 if i < r else 0)
        out.append((start, count))
        start += count
    assert start == total
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("--row-chunks", type=int, default=8)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.row_chunks <= 0:
        raise SystemExit("--row-chunks must be positive")

    artifact_dir = root / "artifacts/kl_predecessor/k19_g14551_16000"
    files = sorted(artifact_dir.glob("raw.*.hex"))
    if not files:
        raise SystemExit(f"no weight hex chunks under {artifact_dir}")

    generated = root / "Erdos1135/KrasikovLagarias/Generated"
    generated.mkdir(parents=True, exist_ok=True)
    for stale in generated.glob("K19Gamma14551HexChunk*.lean"):
        stale.unlink()

    payload_imports: list[str] = []
    payload_refs: list[str] = []
    for i, payload in enumerate(files):
        stem = f"K19Gamma14551HexChunk{i:02d}"
        value = f"k19Gamma14551HexChunk{i:02d}"
        payload_imports.append(
            f"import Erdos1135.KrasikovLagarias.Generated.{stem}"
        )
        payload_refs.append(f"  {value}")
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.ChunkedEncoding

namespace Erdos1135
namespace KrasikovLagarias

/-- One independently elaborated hexadecimal source-certificate fragment. -/
def {value} : String :=
  include_str "../../../artifacts/kl_predecessor/k19_g14551_16000/{payload.name}"

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    data = generated / "K19Gamma14551Data.lean"
    data.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.ChunkedEncoding",
        "import Erdos1135.KrasikovLagarias.RealCertificate",
        "import Erdos1135.KrasikovLagarias.ChunkedStreamingCertificate",
        *payload_imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        "def k19Gamma14551EncodedWeightHexChunks : Array String := #[",
        ",\n".join(payload_refs),
        "]",
        "",
        "def k19Gamma14551EncodedCertificate : FiniteCertificate where",
        "  k := 19",
        "  gammaNum := 14551",
        "  gammaDen := 16000",
        "  coefficients := {",
        "    scale := 281474976710656",
        "    lambdaNeg2 := 79781805157054",
        "    lambdaAlphaMinus2 := 216678499581515",
        "    lambdaAlphaMinus1 := 406990044804623",
        "  }",
        "  weights := decodeU32LEHexChunks k19Gamma14551EncodedWeightHexChunks",
        "",
        "end KrasikovLagarias",
        "end Erdos1135",
        "",
    ]), encoding="utf-8")

    metadata = generated / "K19Gamma14551Metadata.lean"
    metadata.write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551Data

namespace Erdos1135
namespace KrasikovLagarias

theorem k19Gamma14551EncodedEncodingValid :
    u32HexChunksEncodingValid k19Gamma14551EncodedWeightHexChunks
      {TOTAL} = true := by
  native_decide

/-- Stack-safe executable metadata verification.  The public finite-certificate
source defines `metadataCheck` with array folds instead of proposition-level
`Fintype` enumeration over all 387,420,489 rows. -/
theorem k19Gamma14551EncodedCertificate_metadataCheck :
    k19Gamma14551EncodedCertificate.metadataCheck = true := by
  native_decide

theorem k19Gamma14551EncodedCertificate_metadataValid :
    k19Gamma14551EncodedCertificate.MetadataValid :=
  (k19Gamma14551EncodedCertificate.metadataCheck_eq_true_iff).mp
    k19Gamma14551EncodedCertificate_metadataCheck

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    intervals = split_counts(TOTAL, args.row_chunks)
    imports: list[str] = []
    theorem_names: list[str] = []
    for i, (start, count) in enumerate(intervals):
        stem = f"K19Gamma14551Rows{i:02d}"
        theorem = f"k19Gamma14551Rows{i:02d}"
        imports.append(f"import Erdos1135.KrasikovLagarias.Generated.{stem}")
        theorem_names.append(theorem)
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551Metadata

namespace Erdos1135
namespace KrasikovLagarias

theorem {theorem} :
    k19Gamma14551EncodedCertificate.rowsCheckRange {start} {count} = true := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    composition: list[str] = []
    cumulative = intervals[0][1]
    composition.append(f'''private theorem k19Gamma14551RowsThrough00 :
    k19Gamma14551EncodedCertificate.rowsCheckRange 0 {cumulative} = true := by
  simpa using {theorem_names[0]}
''')
    for i in range(1, len(intervals)):
        _start, count = intervals[i]
        previous = cumulative
        cumulative += count
        composition.append(f'''private theorem k19Gamma14551RowsThrough{i:02d} :
    k19Gamma14551EncodedCertificate.rowsCheckRange 0 {cumulative} = true := by
  have hright :
      k19Gamma14551EncodedCertificate.rowsCheckRange (0 + {previous}) {count} = true := by
    simpa using {theorem_names[i]}
  simpa using FiniteCertificate.rowsCheckRange_append
    k19Gamma14551EncodedCertificate 0 {previous} {count}
    k19Gamma14551RowsThrough{i-1:02d} hright
''')
    assert cumulative == TOTAL

    aggregate = generated / "K19Gamma14551.lean"
    aggregate.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551Metadata",
        *imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        *composition,
        f'''theorem k19Gamma14551EncodedCertificate_valid :
    k19Gamma14551EncodedCertificate.Valid :=
  FiniteCertificate.valid_of_metadata_and_full_range
    k19Gamma14551EncodedCertificate_metadataValid
    k19Gamma14551RowsThrough{len(intervals)-1:02d}

theorem k19Gamma14551EncodedCertificate_realRowValid {{index : Nat}}
    (hindex : index < k19Gamma14551EncodedCertificate.principalCount) :
    k19Gamma14551EncodedCertificate.RealRowValid
      (realCoefficients k19Gamma14551EncodedCertificate.gammaNum
        k19Gamma14551EncodedCertificate.gammaDen) index :=
  k19Gamma14551EncodedCertificate_valid.klRealRowValid hindex

end KrasikovLagarias
end Erdos1135
'''
    ]), encoding="utf-8")

    print(f"PAYLOAD_MODULES={len(files)}")
    print(f"ROW_CHUNKS={len(intervals)}")
    for i, (start, count) in enumerate(intervals):
        print(f"CHUNK_{i:02d}_START={start}")
        print(f"CHUNK_{i:02d}_COUNT={count}")
    print("CHUNKED_SOURCE_WRAPPER_GENERATED=PASS")


if __name__ == "__main__":
    main()
