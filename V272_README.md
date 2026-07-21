# V27.2 Actual Inverse Long Gamma — Free/Open Only

V27.2 replaces the previous virtual linear hedge with actual Deribit
`BTC-PERPETUAL` inverse-contract accounting.

## One command

```bash
chmod +x RUN_V272_EVERYTHING.command V272_SAFE_LAUNCHER.sh
./RUN_V272_EVERYTHING.command
```

The one-shot command installs dependencies, runs all authority tests, records
one public snapshot, applies the continuity gate, verifies outputs, and builds:

```text
runtime/V272_Actual_Inverse_Handoff.zip
```

## Continuous collection

Install `V272_SAFE_LAUNCHER.sh` under a macOS LaunchAgent with `RunAtLoad=true`
and `KeepAlive=true`; do not combine it with `StartInterval`.

Default persistent locations:

```text
~/Library/Application Support/V272Free/data/v272_free_chain/
~/Library/Application Support/V272Free/v272_results/
~/Library/Logs/V272Free/
```

## Data and accounting

Only unauthenticated Deribit public JSON-RPC methods are permitted:

```text
public/get_index_price
public/get_instruments
public/ticker
```

Each snapshot contains:

- all available 21–45 DTE expiries;
- up to 11 nearest strikes per expiry, call and put;
- symbols in `HELD_OPTION_STATE.json`;
- one `BTC-PERPETUAL` row with executable bid/ask, mark, index,
  `funding_8h`, `current_funding`, and 10 USD contract size.

The hedge ledger uses:

```text
BTC P&L = signed USD notional × (1 / previous mark − 1 / current mark)
Funding cash = −funding_8h × signed BTC position × elapsed / 8h
Target notional = −option delta in BTC × current index
```

Perpetual changes execute at ask when buying and bid when selling, then pay the
standard registered taker fee. Inverse option premiums and fees are calculated
in BTC and converted to USD at the contemporaneous index.

## Fail-closed gates

No economic metrics are produced until all data gates pass:

- at least 90 active days;
- trailing window or recoverable contiguous suffix passes;
- complete UTC-day snapshot density p10 at least 80%;
- median within-day gap at most 10 minutes;
- maximum within-day operational gap at most 30 minutes.

The economic gate additionally requires:

- held option quote coverage at least 95%;
- every option close has an executable bid;
- perpetual quote coverage at least 95%;
- actual `funding_8h` coverage at least 95%;
- no margin breach or liquidation;
- cost 2×/3× and latency 2/3-bar stress survival.

## Boundaries

V27.2 evaluates one frozen ATM long-straddle plus inverse-perpetual delta hedge.
It does not guarantee future profit or claim that all options strategies are
impossible. Any historical pass is capped at `NEEDS_NEW_OOS`.
