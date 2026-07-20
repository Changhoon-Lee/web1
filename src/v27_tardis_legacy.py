#!/usr/bin/env python3
"""Automatic Tardis downloader for the V27 options-chain input."""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from v27_core import VERSION, sha256_file, write_json


def _date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _month_starts(start: date, end: date) -> list[date]:
    cursor = start.replace(day=1)
    out = []
    while cursor < end:
        if cursor >= start:
            out.append(cursor)
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return out


def download_free_samples(destination: Path, start: date, end: date) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for day in _month_starts(start, end):
        url = f"https://datasets.tardis.dev/v1/deribit/options_chain/{day:%Y/%m/%d}/OPTIONS.csv.gz"
        target = destination / f"deribit_options_chain_{day:%Y-%m-%d}_OPTIONS.csv.gz"
        if not target.exists() or target.stat().st_size == 0:
            try:
                with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as out:
                    out.write(response.read())
            except Exception as exc:
                if target.exists():
                    target.unlink()
                files.append({"date": day.isoformat(), "url": url, "error": f"{type(exc).__name__}: {exc}"})
                continue
        files.append({"date": day.isoformat(), "url": url, "path": str(target), "size": target.stat().st_size, "sha256": sha256_file(target)})
    manifest = {
        "version": VERSION,
        "provider": "Tardis.dev",
        "exchange": "deribit",
        "data_type": "options_chain",
        "symbol": "OPTIONS",
        "mode": "FREE_FIRST_DAY_OF_MONTH_SAMPLES",
        "continuous_history": False,
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    write_json(destination / "TARDIS_DOWNLOAD_MANIFEST.json", manifest)
    return manifest


def download_paid_history(destination: Path, start: date, end: date, api_key: str) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        from tardis_dev import download_datasets
        download_datasets(
            exchange="deribit",
            data_types=["options_chain"],
            symbols=["OPTIONS"],
            from_date=start.isoformat(),
            to_date=end.isoformat(),
            api_key=api_key,
            download_dir=str(destination),
        )
        client = "tardis_dev.download_datasets"
    except ImportError:
        from tardis_dev import datasets
        datasets.download(
            exchange="deribit",
            data_types=["options_chain"],
            symbols=["OPTIONS"],
            from_date=start.isoformat(),
            to_date=end.isoformat(),
            api_key=api_key,
            download_dir=str(destination),
        )
        client = "tardis_dev.datasets.download"
    files = []
    for path in sorted(destination.rglob("*.csv.gz")):
        files.append({"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "version": VERSION,
        "provider": "Tardis.dev",
        "exchange": "deribit",
        "data_type": "options_chain",
        "symbol": "OPTIONS",
        "mode": "AUTHENTICATED_CONTINUOUS_HISTORY",
        "continuous_history": True,
        "client": client,
        "start": start.isoformat(),
        "end_exclusive": end.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    write_json(destination / "TARDIS_DOWNLOAD_MANIFEST.json", manifest)
    return manifest


def download_configured_history(destination: Path) -> dict[str, Any]:
    start = _date(os.getenv("V27_FROM", "2022-01-01"))
    default_end = (datetime.now(timezone.utc).date()).isoformat()
    end = _date(os.getenv("V27_TO", default_end))
    if end <= start:
        raise ValueError("V27_TO must be after V27_FROM")
    api_key = os.getenv("TARDIS_API_KEY", "").strip()
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
