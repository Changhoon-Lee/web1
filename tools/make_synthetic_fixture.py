from pathlib import Path
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / "data" / "deribit_public"
out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(27101)
dates = pd.date_range("2021-01-01", periods=1400, freq="D", tz="UTC")
returns = rng.normal(0.00045, 0.025, len(dates))
price = 29000 * np.exp(np.cumsum(returns))
dvol = 58 + 12 * np.sin(np.linspace(0, 20, len(dates))) + rng.normal(0, 1.5, len(dates))
pd.DataFrame({"timestamp": dates, "index_price": price}).to_csv(out / "btc_index.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
pd.DataFrame({"timestamp": dates, "dvol": dvol}).to_csv(out / "btc_dvol.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
(out / "FREE_DATA_PROVENANCE.json").write_text('{"paid_sources_used":false,"source":"SYNTHETIC_TEST_ONLY"}\n', encoding="utf-8")
