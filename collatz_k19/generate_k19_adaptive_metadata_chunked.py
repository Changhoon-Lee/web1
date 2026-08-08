#!/usr/bin/env python3
"""Generate exact interval-decomposed K19 adaptive metadata proofs.

This is the fallback for environments where evaluating the public monolithic
`metadataCheck` still exhausts Lean's evaluator stack. It preserves the public
`AdaptiveForcedPotentialCertificate.MetadataValid` proposition:

* each hexadecimal payload fragment is independently encoding-checked;
* the decoded array's exact global size is checked once;
* the pointwise value bound is checked on consecutive exact intervals;
* interval results are composed in Lean and promoted to the original public
  `MetadataValid` proposition by `ChunkedMetadataCertificate`.
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
    parser.add_argument("--metadata-chunks", type=int, default=12)
    args = parser.parse_args()
    if args.metadata_chunks <= 0:
        raise SystemExit("--metadata-chunks must be positive")

    root = args.source_root.resolve()
    artifact_dir = root / "artifacts/kl_predecessor/k19_adaptive_potential"
    payloads = sorted(artifact_dir.glob("raw.*.hex"))
    if not payloads:
        raise SystemExit(f"no adaptive-potential hex chunks under {artifact_dir}")

    generated = root / "Erdos1135/KrasikovLagarias/Generated"
    generated.mkdir(parents=True, exist_ok=True)

    # Each raw file consists of exactly two hexadecimal characters per value.
    payload_counts: list[int] = []
    validity_imports: list[str] = []
    for i, payload in enumerate(payloads):
        chars = payload.stat().st_size
        if chars % 2 != 0:
            raise SystemExit(f"odd hexadecimal character count in {payload}: {chars}")
        count = chars // 2
        payload_counts.append(count)
        chunk_stem = f"K19AdaptiveForcedPotentialHexChunk{i:02d}"
        chunk_value = f"k19AdaptiveForcedPotentialHexChunk{i:02d}"
        validity_stem = f"K19AdaptiveForcedPotentialHexValidity{i:02d}"
        validity_theorem = f"k19AdaptiveForcedPotentialHexValidity{i:02d}"
        validity_imports.append(
            f"import Erdos1135.KrasikovLagarias.Generated.{validity_stem}"
        )
        (generated / f"{validity_stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.Generated.{chunk_stem}
import Erdos1135.KrasikovLagarias.ForcedPotentialCertificate

namespace Erdos1135
namespace KrasikovLagarias

theorem {validity_theorem} :
    u8HexEncodingValid {chunk_value} {count} = true := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    if sum(payload_counts) != TOTAL:
        raise SystemExit(
            f"decoded payload count mismatch: {sum(payload_counts)} != {TOTAL}"
        )

    base = generated / "K19AdaptiveForcedPotentialMetadataBase.lean"
    base.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialData",
        "import Erdos1135.KrasikovLagarias.ChunkedMetadataCertificate",
        *validity_imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        "theorem k19AdaptiveForcedPotentialCertificate_levelValid :",
        "    2 ≤ k19AdaptiveForcedPotentialCertificate.k := by",
        "  native_decide",
        "",
        "theorem k19AdaptiveForcedPotentialCertificate_principalCount :",
        f"    EliminationResidue.principalCount",
        f"      k19AdaptiveForcedPotentialCertificate.k = {TOTAL} := by",
        "  native_decide",
        "",
        "theorem k19AdaptiveForcedPotentialCertificate_sizeValid :",
        "    k19AdaptiveForcedPotentialCertificate.values.size =",
        "      EliminationResidue.principalCount",
        "        k19AdaptiveForcedPotentialCertificate.k := by",
        "  native_decide",
        "",
        "end KrasikovLagarias",
        "end Erdos1135",
        "",
    ]), encoding="utf-8")

    intervals = split_counts(TOTAL, args.metadata_chunks)
    interval_imports: list[str] = []
    interval_theorems: list[str] = []
    for i, (start, count) in enumerate(intervals):
        stem = f"K19AdaptiveForcedPotentialMetadataBounds{i:02d}"
        theorem = f"k19AdaptiveForcedPotentialMetadataBounds{i:02d}"
        interval_imports.append(
            f"import Erdos1135.KrasikovLagarias.Generated.{stem}"
        )
        interval_theorems.append(theorem)
        (generated / f"{stem}.lean").write_text(f'''import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialMetadataBase

namespace Erdos1135
namespace KrasikovLagarias

theorem {theorem} :
    k19AdaptiveForcedPotentialCertificate.metadataBoundsCheckRange
      {start} {count} = true := by
  native_decide

end KrasikovLagarias
end Erdos1135
''', encoding="utf-8")

    compositions: list[str] = []
    cumulative = intervals[0][1]
    compositions.append(f'''private theorem k19AdaptiveMetadataBoundsThrough00 :
    k19AdaptiveForcedPotentialCertificate.metadataBoundsCheckRange
      0 {cumulative} = true := by
  simpa using {interval_theorems[0]}
''')
    for i in range(1, len(intervals)):
        _start, count = intervals[i]
        previous = cumulative
        cumulative += count
        compositions.append(f'''private theorem k19AdaptiveMetadataBoundsThrough{i:02d} :
    k19AdaptiveForcedPotentialCertificate.metadataBoundsCheckRange
      0 {cumulative} = true := by
  have hright :
      k19AdaptiveForcedPotentialCertificate.metadataBoundsCheckRange
        (0 + {previous}) {count} = true := by
    simpa using {interval_theorems[i]}
  simpa using
    AdaptiveForcedPotentialCertificate.metadataBoundsCheckRange_append
      k19AdaptiveForcedPotentialCertificate
      0 {previous} {count}
      k19AdaptiveMetadataBoundsThrough{i-1:02d} hright
''')
    assert cumulative == TOTAL

    metadata = generated / "K19AdaptiveForcedPotentialMetadata.lean"
    metadata.write_text("\n".join([
        "import Erdos1135.KrasikovLagarias.Generated.K19AdaptiveForcedPotentialMetadataBase",
        *interval_imports,
        "",
        "namespace Erdos1135",
        "namespace KrasikovLagarias",
        "",
        *compositions,
        "theorem k19AdaptiveForcedPotentialCertificate_metadataValid :",
        "    k19AdaptiveForcedPotentialCertificate.MetadataValid := by",
        "  apply",
        "    AdaptiveForcedPotentialCertificate.metadataValid_of_size_and_full_bounds",
        "      k19AdaptiveForcedPotentialCertificate_levelValid",
        "      k19AdaptiveForcedPotentialCertificate_sizeValid",
        "  rw [k19AdaptiveForcedPotentialCertificate_principalCount]",
        f"  exact k19AdaptiveMetadataBoundsThrough{len(intervals)-1:02d}",
        "",
        "end KrasikovLagarias",
        "end Erdos1135",
        "",
    ]), encoding="utf-8")

    print(f"PAYLOAD_VALIDITY_MODULES={len(payloads)}")
    for i, count in enumerate(payload_counts):
        print(f"PAYLOAD_{i:02d}_VALUES={count}")
    print(f"METADATA_CHUNKS={len(intervals)}")
    for i, (start, count) in enumerate(intervals):
        print(f"METADATA_{i:02d}_START={start}")
        print(f"METADATA_{i:02d}_COUNT={count}")
    print("CHUNKED_ADAPTIVE_METADATA_GENERATED=PASS")


if __name__ == "__main__":
    main()
