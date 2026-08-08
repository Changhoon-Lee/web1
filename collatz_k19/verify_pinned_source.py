#!/usr/bin/env python3
"""Hard-fail unless the formal base matches the published pinned snapshot."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

PINNED_COMMIT = "5f76a170e74ea5b0c37c56683bd4c1e9d72e5e3f"
HASHES = {
    "CollatzPredecessor090.lean": "26167a4c873b05bd2ad86580d72519c3d5fdc73194625034145041de51cb12eb",
    "Erdos1135/KrasikovLagarias/AdaptiveForcedPotentialCertificate.lean": "ff69a1a725acee11b77f566b68309ff78f80378941af9aaedce19c83048a86ff",
    "Erdos1135/KrasikovLagarias/Asymptotic.lean": "683dfa25e3c15a379b02ffcf090a2c49811996059c4b7efc156ee1a1fccfecc7",
    "Erdos1135/KrasikovLagarias/Certificate.lean": "c1cc4033292dece680259cc7f43b1e28f17d5de5ea008352222756404c93cd56",
    "Erdos1135/KrasikovLagarias/ChunkedEncoding.lean": "c28571464325f87a995b401d0e41701f784fcdba5a65ea445f4bb7e2ffc11ac5",
    "Erdos1135/KrasikovLagarias/RealCertificate.lean": "82b680d59b3f68fbb61e765142e2f418485bdc44cd67cfc507a48c86bdd918b2",
    "Erdos1135/KrasikovLagarias/Generated/K18AdaptiveForcedPotential.lean": "580fd0bb308387096b6435637bbdf7f185e6c895c7bb3852e7789718a59249d6",
    "Erdos1135/KrasikovLagarias/Generated/K18Gamma901.lean": "f7deee98bc6804575cf4d69d7a571b0cb863b1151a90a37be11d13d3f5e32547",
    "Erdos1135/KrasikovLagarias/K18CoefficientBridge.lean": "71f2bdbfcc24c719eefbd4fec9c1a45f2625dcd9fda216a58abc32bf7f97a091",
    "Erdos1135/KrasikovLagarias/K18CriticalChoice.lean": "ed46add5588d7402dd0005a30e053bac6f57f444419803b8d7b3ba89459a765b",
    "Erdos1135/KrasikovLagarias/K18PowerOfTwoTargets.lean": "4fea322131440d30f236c0c34c827a0c216fbf4efb068f90b922ea850ee5b7ca",
    "Erdos1135/KrasikovLagarias/K18PredecessorAllTargets.lean": "465df578bb4e03dcfc9b4687e23b963ad444f4efa980d98e82622e429535c087",
    "Erdos1135/KrasikovLagarias/K18PredecessorBridge.lean": "2394884574c4b44e9c7b178e549755364df7fd5a623dcc6835db72314f2c2d81",
    "Erdos1135/KrasikovLagarias/K18PrincipalIndex.lean": "0ac1c1eb021b26e487a565d2ed584d40f66dcd81bb2c93dddd415f9ff677d578",
    "Erdos1135/KrasikovLagarias/K18SourceBridge.lean": "9b59b209f05119419d6bf992dc0b6b3f66aba7bc3b163e4eeee9d246fc4fc810",
    "lakefile.toml": "4a8cae0459d9fc56c48a06f164e8dc1f75ce09b0d5ec2ef4bff7b3447be2b4be",
    "lean-toolchain": "ce4c4e3d87434b9663f46de25ce34b48a0cf0d392e0a320a0787b4674a2d7b61",
}

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    failures: list[str] = []
    for rel, expected in HASHES.items():
        path = root / rel
        if not path.is_file():
            failures.append(f"MISSING\t{rel}")
            continue
        actual = sha256(path)
        if actual != expected:
            failures.append(f"HASH_MISMATCH\t{rel}\t{expected}\t{actual}")
    if failures:
        print("\n".join(failures))
        raise SystemExit("PINNED_SOURCE=FAIL")
    print(f"PINNED_COMMIT={PINNED_COMMIT}")
    print(f"FILES_VERIFIED={len(HASHES)}")
    print("PINNED_SOURCE=PASS")

if __name__ == "__main__":
    main()
