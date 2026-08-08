#!/usr/bin/env python3
"""Generate a source-LP K19 wrapper split into native-decidable row intervals.

Precondition: hexadecimal payload chunks already exist under
artifacts/kl_predecessor/k19_g14551_16000.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TOTAL = 387_420_489


def includes(relative: str, files: list[Path]) -> str:
    return ",\n".join(
        f'  include_str "../../../artifacts/kl_predecessor/{relative}/{p.name}"'
        for p in files
    )


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
    ap = argparse.ArgumentParser()
    ap.add_argument("source_root", type=Path)
    ap.add_argument("--row-chunks", type=int, default=16)
    ns = ap.parse_args()
    root = ns.source_root.resolve()
    if ns.row_chunks <= 0:
        raise SystemExit("--row-chunks must be positive")
    artifact_dir = root / "artifacts/kl_predecessor/k19_g14551_16000"
    files = sorted(artifact_dir.glob("raw.*.hex"))
    if not files:
        raise SystemExit(f"no weight hex chunks under {artifact_dir}")
    generated = root / "Erdos1135/KrasikovLagarias/Generated"
    generated.mkdir(parents=True, exist_ok=True)

    data = generated / "K19Gamma14551Data.lean"
    data.write_text(f'''import Erdos1135.KrasikovLagarias.ChunkedEncoding
import Erdos1135.KrasikovLagarias.RealCertificate
import Erdos1135.KrasikovLagarias.ChunkedStreamingCertificate

namespace Erdos1135
namespace KrasikovLagarias

def k19Gamma14551EncodedWeightHexChunks : Array String := #[
{includes("k19_g14551_16000", files)}
]

def k19Gamma14551EncodedCertificate : FiniteCertificate where
  k := 19
  gammaNum := 14551
  gammaDen := 16000
  coefficients := {{
    scale := 281474976710656
    lambdaNeg2 := 79781805157054
    lambdaAlphaMinus2 := 216678499581515
    lambdaAlphaMinus1 := 406990044804623
  }}
  weights := decodeU32LEHexChunks k19Gamma14551EncodedWeightHexChunks

theorem k19Gamma14551EncodedEncodingValid :
    u32HexChunksEncodingValid k19Gamma14551EncodedWeightHexChunks
      {TOTAL} = true := by
  native_decide

theorem k19Gamma14551EncodedCertificate_metadataValid :
    k19Gamma14551EncodedCertificate.MetadataValid := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    intervals = split_counts(TOTAL, ns.row_chunks)
    imports: list[str] = []
    theorem_names: list[str] = []
    for i, (start, count) in enumerate(intervals):
        stem = f"K19Gamma14551Rows{i:02d}"
        theorem = f"k19Gamma14551Rows{i:02d}"
        imports.append(f"import Erdos1135.KrasikovLagarias.Generated.{stem}")
        theorem_names.append(theorem)
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551Data

namespace Erdos1135
namespace KrasikovLagarias

theorem {theorem} :
    k19Gamma14551EncodedCertificate.rowsCheckRange {start} {count} = true := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    lines: list[str] = []
    cumulative = intervals[0][1]
    lines.append(f'''private theorem k19Gamma14551RowsThrough00 :
    k19Gamma14551EncodedCertificate.rowsCheckRange 0 {cumulative} = true := by
  simpa using {theorem_names[0]}
''')
    for i in range(1, len(intervals)):
        _start, count = intervals[i]
        prev = cumulative
        cumulative += count
        lines.append(f'''private theorem k19Gamma14551RowsThrough{i:02d} :
    k19Gamma14551EncodedCertificate.rowsCheckRange 0 {cumulative} = true := by
  have hright :
      k19Gamma14551EncodedCertificate.rowsCheckRange (0 + {prev}) {count} = true := by
    simpa using {theorem_names[i]}
  simpa using FiniteCertificate.rowsCheckRange_append
    k19Gamma14551EncodedCertificate 0 {prev} {count}
    k19Gamma14551RowsThrough{i-1:02d} hright
''')
    assert cumulative == TOTAL

    aggregate = generated / "K19Gamma14551.lean"
    aggregate.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.Generated.K19Gamma14551Data",
        *imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        *lines,
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

    print(f"ROW_CHUNKS={len(intervals)}")
    for i, (start, count) in enumerate(intervals):
        print(f"CHUNK_{i:02d}_START={start}")
        print(f"CHUNK_{i:02d}_COUNT={count}")
    print("CHUNKED_SOURCE_WRAPPER_GENERATED=PASS")


if __name__ == "__main__":
    main()
