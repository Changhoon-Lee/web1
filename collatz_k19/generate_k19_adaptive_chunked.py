#!/usr/bin/env python3
"""Generate a K19 adaptive-potential wrapper split at two exact boundaries.

The payload text is split into one Lean module per hexadecimal file so that no
single elaboration unit contains the complete 774 MB textual payload. Row
validity is independently split into consecutive native-decidable intervals.
Both decompositions are recombined inside Lean without changing the public
`AdaptiveForcedPotentialCertificate.Valid` proposition.
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

    artifact_dir = root / "artifacts/kl_predecessor/k19_adaptive_potential"
    files = sorted(artifact_dir.glob("raw.*.hex"))
    if not files:
        raise SystemExit(f"no adaptive-potential hex chunks under {artifact_dir}")

    generated = root / "Erdos1135/KrasikovLagarias/Generated"
    generated.mkdir(parents=True, exist_ok=True)
    for stale in generated.glob("K19AdaptiveForcedPotentialHexChunk*.lean"):
        stale.unlink()

    payload_imports: list[str] = []
    payload_refs: list[str] = []
    for i, payload in enumerate(files):
        stem = f"K19AdaptiveForcedPotentialHexChunk{i:02d}"
        value = f"k19AdaptiveForcedPotentialHexChunk{i:02d}"
        payload_imports.append(
            f"import Erdos1135.KrasikovLagarias.Generated.{stem}"
        )
        payload_refs.append(f"  {value}")
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.ChunkedEncoding

namespace Erdos1135
namespace KrasikovLagarias

/-- One independently elaborated hexadecimal payload fragment. -/
def {value} : String :=
  include_str "../../../artifacts/kl_predecessor/k19_adaptive_potential/{payload.name}"

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    data = generated / "K19AdaptiveForcedPotentialData.lean"
    data.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.AdaptiveForcedPotentialCertificate",
        "import Erdos1135.KrasikovLagarias.ChunkedEncoding",
        "import Erdos1135.KrasikovLagarias.ChunkedStreamingCertificate",
        *payload_imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        "def k19AdaptiveForcedPotentialHexChunks : Array String := #[",
        ",\n".join(payload_refs),
        "]",
        "",
        "def k19AdaptiveForcedPotentialCertificate :",
        "    AdaptiveForcedPotentialCertificate where",
        "  k := 19",
        "  bound := 36",
        "  values := decodeU8HexChunks k19AdaptiveForcedPotentialHexChunks",
        "",
        "end KrasikovLagarias",
        "end Erdos1135",
        "",
    ]), encoding="utf-8")

    metadata = generated / "K19AdaptiveForcedPotentialMetadata.lean"
    metadata.write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialData

namespace Erdos1135
namespace KrasikovLagarias

theorem k19AdaptiveForcedPotentialEncodingValid :
    u8HexChunksEncodingValid k19AdaptiveForcedPotentialHexChunks
      {TOTAL} = true := by
  native_decide

/-- Stack-safe executable metadata verification. The public source defines
`metadataCheck` with `Array.all` specifically to avoid the proposition-level
`Fintype` decision procedure over hundreds of millions of entries. -/
theorem k19AdaptiveForcedPotentialCertificate_metadataCheck :
    k19AdaptiveForcedPotentialCertificate.metadataCheck = true := by
  native_decide

theorem k19AdaptiveForcedPotentialCertificate_metadataValid :
    k19AdaptiveForcedPotentialCertificate.MetadataValid :=
  (k19AdaptiveForcedPotentialCertificate.metadataCheck_eq_true_iff).mp
    k19AdaptiveForcedPotentialCertificate_metadataCheck

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    intervals = split_counts(TOTAL, args.row_chunks)
    imports: list[str] = []
    theorem_names: list[str] = []
    for i, (start, count) in enumerate(intervals):
        stem = f"K19AdaptiveForcedPotentialRows{i:02d}"
        theorem = f"k19AdaptiveForcedPotentialRows{i:02d}"
        imports.append(f"import Erdos1135.KrasikovLagarias.Generated.{stem}")
        theorem_names.append(theorem)
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialMetadata

namespace Erdos1135
namespace KrasikovLagarias

theorem {theorem} :
    k19AdaptiveForcedPotentialCertificate.rowsCheckRange
      k19AdaptiveForcedPotentialCertificate_metadataValid {start} {count} = true := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    composition: list[str] = []
    cumulative = intervals[0][1]
    composition.append(f'''private theorem k19AdaptiveRowsThrough00 :
    k19AdaptiveForcedPotentialCertificate.rowsCheckRange
      k19AdaptiveForcedPotentialCertificate_metadataValid 0 {cumulative} = true := by
  simpa using {theorem_names[0]}
''')
    for i in range(1, len(intervals)):
        _start, count = intervals[i]
        previous = cumulative
        cumulative += count
        composition.append(f'''private theorem k19AdaptiveRowsThrough{i:02d} :
    k19AdaptiveForcedPotentialCertificate.rowsCheckRange
      k19AdaptiveForcedPotentialCertificate_metadataValid 0 {cumulative} = true := by
  have hright :
      k19AdaptiveForcedPotentialCertificate.rowsCheckRange
        k19AdaptiveForcedPotentialCertificate_metadataValid (0 + {previous}) {count} = true := by
    simpa using {theorem_names[i]}
  simpa using AdaptiveForcedPotentialCertificate.rowsCheckRange_append
    k19AdaptiveForcedPotentialCertificate
    k19AdaptiveForcedPotentialCertificate_metadataValid
    0 {previous} {count}
    k19AdaptiveRowsThrough{i-1:02d} hright
''')
    assert cumulative == TOTAL

    aggregate = generated / "K19AdaptiveForcedPotential.lean"
    aggregate.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialMetadata",
        *imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        *composition,
        f'''theorem k19AdaptiveForcedPotentialCertificate_valid :
    k19AdaptiveForcedPotentialCertificate.Valid :=
  AdaptiveForcedPotentialCertificate.valid_of_metadata_and_full_range
    k19AdaptiveForcedPotentialCertificate_metadataValid
    k19AdaptiveRowsThrough{len(intervals)-1:02d}

def k19AdaptiveForcedPotential :
    AdaptiveEliminationPolicy.ForcedPotential 19 (by norm_num) :=
  k19AdaptiveForcedPotentialCertificate_valid.toForcedPotential

end KrasikovLagarias
end Erdos1135
'''
    ]), encoding="utf-8")

    print(f"PAYLOAD_MODULES={len(files)}")
    print(f"ROW_CHUNKS={len(intervals)}")
    for i, (start, count) in enumerate(intervals):
        print(f"CHUNK_{i:02d}_START={start}")
        print(f"CHUNK_{i:02d}_COUNT={count}")
    print("CHUNKED_ADAPTIVE_WRAPPER_GENERATED=PASS")


if __name__ == "__main__":
    main()
