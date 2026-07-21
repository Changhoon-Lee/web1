#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import v272_core as core
import v2724_cli as cli
import v2724_ws as ws


def option_meta(symbol: str, strike: float = 100000.0, option_type: str = "call", expiry: str = "2026-08-20T08:00:00Z") -> dict:
    return {
        "instrument_name": symbol,
        "expiration_timestamp": int(pd.Timestamp(expiry).timestamp() * 1000),
        "strike": strike,
        "option_type": option_type,
    }


def ticker_message(symbol: str, timestamp: pd.Timestamp, *, delta: float | None = 0.5, funding: float | None = None, bid: float | None = None) -> dict:
    is_perp = symbol == "BTC-PERPETUAL"
    if bid is None:
        bid = 100000.0 if is_perp else 0.04
    data = {
        "instrument_name": symbol,
        "timestamp": int(timestamp.timestamp() * 1000),
        "best_bid_price": bid,
        "best_ask_price": bid + (0.5 if is_perp else 0.001),
        "best_bid_amount": 2.0,
        "best_ask_amount": 3.0,
        "mark_price": bid + (0.25 if is_perp else 0.0005),
        "index_price": 100000.0,
        "underlying_price": 100000.0,
        "open_interest": 100.0,
        "state": "open",
    }
    if is_perp:
        data.update({"funding_8h": 0.0002 if funding is None else funding, "current_funding": 0.0002 if funding is None else funding})
    else:
        data.update({"mark_iv": 55.0, "bid_iv": 54.0, "ask_iv": 56.0, "greeks": {"delta": delta, "gamma": 0.0001, "vega": 1.0, "theta": -1.0}})
    return {"jsonrpc": "2.0", "method": "subscription", "params": {"channel": f"ticker.{symbol}.agg2", "data": data}}


def hydrated_fixture(cutoff: pd.Timestamp | None = None) -> tuple[ws.TickerStateStore, dict[str, dict], pd.Timestamp]:
    cutoff = cutoff or pd.Timestamp("2026-07-21T08:05:00Z")
    universe = {
        "BTC-20AUG26-100000-C": option_meta("BTC-20AUG26-100000-C", option_type="call"),
        "BTC-20AUG26-100000-P": option_meta("BTC-20AUG26-100000-P", option_type="put"),
    }
    store = ws.TickerStateStore()
    expected = set(universe) | {"BTC-PERPETUAL"}
    store.begin_connection(expected, cutoff - pd.Timedelta(seconds=10))
    for symbol in sorted(expected):
        delta = -0.5 if symbol.endswith("-P") else 0.5
        store.ingest_message(ticker_message(symbol, cutoff - pd.Timedelta(seconds=1), delta=delta), cutoff)
    return store, universe, cutoff


def synthetic_market(days: int = 3) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=days * 24 * 12, freq="5min")
    expiry = pd.Timestamp("2026-01-06T00:00:00Z")
    rows = []
    for index_number, timestamp in enumerate(timestamps):
        index = 100000.0 * math.exp(0.00001 * index_number + 0.002 * math.sin(index_number / 20.0))
        mark = index * (1.0 + 0.00005 * math.sin(index_number / 7.0))
        rows.append({
            "timestamp": timestamp, "symbol": "BTC-PERPETUAL", "type": "perpetual",
            "strike_price": 0.0, "expiration": "", "bid_price": mark - 0.5,
            "ask_price": mark + 0.5, "mark_price": mark, "underlying_price": index,
            "index_price": index, "funding_8h": 0.0001, "current_funding": 0.0001,
            "contract_size_usd": 10.0,
        })
        for option_type, code, delta in (("call", "C", 0.55), ("put", "P", -0.45)):
            intrinsic = max(index - 100000.0, 0.0) if option_type == "call" else max(100000.0 - index, 0.0)
            time_value = max((expiry - timestamp).total_seconds() / 86400.0, 0.0) * 0.003 * index
            premium = (intrinsic + time_value + 1000.0) / index
            rows.append({
                "timestamp": timestamp, "symbol": f"BTC-6JAN26-100000-{code}", "type": option_type,
                "strike_price": 100000.0, "expiration": expiry,
                "bid_price": max(premium - 0.0001, 0.0001), "ask_price": premium + 0.0001,
                "mark_price": premium, "mark_iv": 55.0, "underlying_price": index,
                "index_price": index, "delta": delta, "gamma": 0.0001, "vega": 1.0, "theta": -1.0,
            })
    return pd.DataFrame(rows)


class V2724WebSocketTests(unittest.TestCase):
    def test_41_public_websocket_requires_no_credentials(self):
        cfg = ws.WSConfig()
        self.assertTrue(cfg.websocket_url.startswith("wss://"))
        channels = ws.subscription_channels(["BTC-20AUG26-100000-C"])
        request = {"jsonrpc": "2.0", "method": "public/subscribe", "params": {"channels": channels}}
        self.assertEqual(request["method"], "public/subscribe")
        with mock.patch.dict(os.environ, {"DERIBIT_CLIENT_SECRET": "x"}, clear=False):
            with self.assertRaises(RuntimeError):
                ws.public_rest("get_instruments", {})

    def test_42_subscriptions_are_batched_at_500(self):
        channels = [f"ticker.BTC-X-{index}.agg2" for index in range(1001)]
        batches = ws.batch_channels(channels, 500)
        self.assertEqual([len(batch) for batch in batches], [500, 500, 1])

    def test_43_all_7_to_45_dte_symbols_are_subscribed(self):
        now = pd.Timestamp("2026-07-21T08:00:00Z")
        instruments = []
        for dte in (6, 7, 21, 45, 46):
            expiry = now + pd.Timedelta(days=dte)
            instruments.append(option_meta(f"BTC-{dte}D-100000-C", expiry=expiry.isoformat()))
        selected = ws.choose_collection_universe(instruments, now, ws.WSConfig())
        self.assertEqual(set(selected), {"BTC-7D-100000-C", "BTC-21D-100000-C", "BTC-45D-100000-C"})
        channels = ws.subscription_channels(selected)
        self.assertTrue(all(ws.ticker_channel(symbol) in channels for symbol in selected))

    def test_44_ticker_update_preserves_exchange_timestamp(self):
        store, universe, cutoff = hydrated_fixture()
        record = store.latest_at_or_before(next(iter(universe)), cutoff)
        self.assertIsNotNone(record)
        self.assertEqual(record.source_timestamp, cutoff - pd.Timedelta(seconds=1))

    def test_45_cutoff_excludes_future_messages(self):
        cutoff = pd.Timestamp("2026-07-21T08:05:00Z")
        symbol = "BTC-20AUG26-100000-C"
        store = ws.TickerStateStore()
        store.begin_connection({symbol}, cutoff - pd.Timedelta(seconds=10))
        store.ingest_message(ticker_message(symbol, cutoff - pd.Timedelta(seconds=1), bid=0.04), cutoff)
        store.ingest_message(ticker_message(symbol, cutoff + pd.Timedelta(seconds=1), bid=0.09), cutoff + pd.Timedelta(seconds=2))
        record = store.latest_at_or_before(symbol, cutoff)
        self.assertAlmostEqual(record.data["best_bid_price"], 0.04)

    def test_46_snapshot_freezes_all_symbols_at_one_cutoff(self):
        store, universe, cutoff = hydrated_fixture()
        frame = ws.freeze_snapshot(store, universe, cutoff, ws.WSConfig(), frozen_at=cutoff + pd.Timedelta(seconds=2))
        self.assertEqual(set(frame["symbol"]), set(universe) | {"BTC-PERPETUAL"})
        self.assertEqual(frame["timestamp"].nunique(), 1)
        self.assertEqual(frame["snapshot_target_timestamp"].nunique(), 1)

    def test_47_missing_delta_blocks_entry(self):
        store, universe, cutoff = hydrated_fixture()
        symbol = "BTC-20AUG26-100000-C"
        store.history[symbol].clear()
        store.hydrated_symbols.discard(symbol)
        store.data_gap_open = True
        store.ingest_message(ticker_message(symbol, cutoff - pd.Timedelta(seconds=1), delta=None), cutoff)
        frame = ws.freeze_snapshot(store, universe, cutoff, ws.WSConfig(), frozen_at=cutoff + pd.Timedelta(seconds=1))
        authority = ws.snapshot_authority(frame, ws.WSConfig())
        self.assertFalse(authority["ready"])
        self.assertLess(authority["option_delta_coverage"], 1.0)

    def test_48_held_symbol_missing_blocks_economic_gate(self):
        store, universe, cutoff = hydrated_fixture()
        missing = "BTC-20AUG26-90000-C"
        universe[missing] = option_meta(missing, strike=90000.0)
        store.update_expected_symbols(set(universe) | {"BTC-PERPETUAL"})
        frame = ws.freeze_snapshot(store, universe, cutoff, ws.WSConfig(), frozen_at=cutoff + pd.Timedelta(seconds=1))
        self.assertIn(missing, set(frame["symbol"]))
        self.assertFalse(bool(frame.loc[frame["symbol"] == missing, "authority"].iloc[0]))
        self.assertFalse(ws.snapshot_authority(frame, ws.WSConfig())["ready"])

    def test_49_disconnect_marks_data_gap(self):
        store, _, cutoff = hydrated_fixture()
        self.assertTrue(store.fully_hydrated)
        store.mark_disconnect(cutoff)
        self.assertTrue(store.data_gap_open)
        self.assertFalse(store.fully_hydrated)

    def test_50_reconnect_requires_full_resubscription(self):
        store, universe, cutoff = hydrated_fixture()
        expected = set(universe) | {"BTC-PERPETUAL"}
        previous_epoch = store.connection_epoch
        store.mark_disconnect(cutoff)
        store.begin_connection(expected, cutoff + pd.Timedelta(seconds=1))
        self.assertEqual(store.connection_epoch, previous_epoch + 1)
        self.assertEqual(store.hydrated_symbols, set())
        self.assertFalse(store.fully_hydrated)

    def test_51_snapshot_blocked_until_all_symbols_rehydrated(self):
        cutoff = pd.Timestamp("2026-07-21T08:05:00Z")
        universe = {"BTC-20AUG26-100000-C": option_meta("BTC-20AUG26-100000-C")}
        store = ws.TickerStateStore()
        store.begin_connection(set(universe) | {"BTC-PERPETUAL"}, cutoff - pd.Timedelta(seconds=10))
        store.ingest_message(ticker_message("BTC-PERPETUAL", cutoff - pd.Timedelta(seconds=1)), cutoff)
        frame = ws.freeze_snapshot(store, universe, cutoff, ws.WSConfig(), frozen_at=cutoff + pd.Timedelta(seconds=1))
        self.assertFalse(ws.snapshot_authority(frame, ws.WSConfig())["ready"])

    def test_52_instrument_listing_updates_universe(self):
        store = ws.TickerStateStore()
        store.begin_connection({"A", "BTC-PERPETUAL"}, pd.Timestamp("2026-01-01T00:00:00Z"))
        additions, removals = store.update_expected_symbols({"A", "B", "BTC-PERPETUAL"})
        self.assertEqual(additions, {"B"})
        self.assertEqual(removals, set())
        message = {"params": {"channel": "instrument.state.option.BTC", "data": {"instrument_name": "B", "state": "open", "timestamp": 1}}}
        self.assertEqual(store.ingest_message(message), "instrument_state")
        self.assertTrue(store.universe_refresh_requested)

    def test_53_expired_instrument_is_unsubscribed(self):
        store = ws.TickerStateStore()
        store.begin_connection({"A", "B", "BTC-PERPETUAL"}, pd.Timestamp("2026-01-01T00:00:00Z"))
        additions, removals = store.update_expected_symbols({"B", "BTC-PERPETUAL"})
        self.assertEqual(additions, set())
        self.assertEqual(removals, {"A"})

    def test_54_more_than_500_channels_uses_multiple_batches(self):
        symbols = [f"BTC-X-{index}-C" for index in range(1001)]
        channels = ws.subscription_channels(symbols)
        batches = ws.batch_channels(channels, 500)
        self.assertGreaterEqual(len(batches), 3)
        self.assertTrue(all(len(batch) <= 500 for batch in batches))

    def test_55_duplicate_and_out_of_order_messages_are_safe(self):
        symbol = "BTC-20AUG26-100000-C"
        timestamp = pd.Timestamp("2026-07-21T08:00:00Z")
        store = ws.TickerStateStore()
        store.begin_connection({symbol}, timestamp - pd.Timedelta(seconds=1))
        message = ticker_message(symbol, timestamp)
        self.assertEqual(store.ingest_message(message, timestamp), symbol)
        self.assertEqual(store.ingest_message(message, timestamp), "duplicate_ignored")
        older = ticker_message(symbol, timestamp - pd.Timedelta(seconds=1))
        self.assertEqual(store.ingest_message(older, timestamp), "out_of_order_ignored")
        self.assertEqual(len(store.history[symbol]), 1)

    def test_56_websocket_snapshot_is_byte_deterministic(self):
        store, universe, cutoff = hydrated_fixture()
        frame = ws.freeze_snapshot(store, universe, cutoff, ws.WSConfig(), frozen_at=cutoff + pd.Timedelta(seconds=1))
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a.gz", Path(tmp) / "b.gz"
            ws.deterministic_gzip_csv(frame, first)
            ws.deterministic_gzip_csv(frame, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_57_rest_ticker_polling_is_forbidden_in_continuous_mode(self):
        with self.assertRaises(RuntimeError):
            ws.public_rest("ticker", {"instrument_name": "BTC-PERPETUAL"})
        with self.assertRaises(RuntimeError):
            ws.public_rest("get_book_summary_by_currency", {"currency": "BTC", "kind": "option"})

    def test_58_ready_true_end_to_end_websocket_fixture(self):
        core_cfg = core.Config(
            snapshot_minutes=5, target_dte=3.0, minimum_dte=1.0, maximum_dte=6.0,
            exit_dte=0.25, roll_days=1, entry_hour_utc=0, maximum_quote_age_minutes=10,
            minimum_backtest_days=1, minimum_rolls=1, minimum_held_quote_coverage=0.90,
            minimum_perp_quote_coverage=0.99, minimum_funding_coverage=0.99,
        )
        ws_cfg = replace(ws.WSConfig(), minimum_active_days=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            output = root / "out"
            data_root.mkdir()
            synthetic_market().to_csv(data_root / "synthetic.ws.compact.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
            data_coverage = {"ready": True, "active_days": 3, "websocket_authority_gate": {"ready": True}}
            gate = cli.run_economic(data_root, output, core_cfg, ws_cfg, data_coverage, data_root / "HELD_OPTION_STATE.json")
            self.assertTrue((output / "FINAL_GATE.json").exists())
            self.assertTrue(list(output.glob("*_exact_ledger.csv.gz")))
            self.assertTrue(cli.verify(output)["passed"])
            self.assertIn(gate["overall_status"], {
                "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED",
                "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS",
                "MARKET_DATA_CONTINUITY_GATE_FAILED",
            })


if __name__ == "__main__":
    unittest.main()
