#!/usr/bin/env python3
"""Authoritative V27 Tardis downloader with bounded free-sample defaults."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import v27_tardis_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)


def download_configured_history(destination: Path) -> dict[str, Any]:
    api_key = os.getenv("TARDIS_API_KEY", "").strip()
    today = datetime.now(timezone.utc).date()
    if os.getenv("V27_FROM"):
        start = _date(os.environ["V27_FROM"])
    else:
        start = _date("2022-01-01") if api_key else today - timedelta(days=365)
    end = _date(os.getenv("V27_TO", today.isoformat()))
    if end <= start:
        raise ValueError("V27_TO must be after V27_FROM")
    if api_key:
        return download_paid_history(destination, start, end, api_key)
    return download_free_samples(destination, start, end)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = Path(os.getenv("V27_TARDIS_DIR", str(root / "data/v27_tardis"))).expanduser().resolve()
    result = download_configured_history(destination)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
