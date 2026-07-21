# V27.2.1 Actual Inverse Long Gamma — Free/Open Only

V27.2.1 replaces the previous virtual linear hedge with actual Deribit
`BTC-PERPETUAL` inverse-contract accounting. It also inserts an authoritative
pre-trade equity row, so option spread, option fees, hedge execution costs, and
funding are included in every wealth, CAGR, Sharpe, and drawdown calculation.

## One command

```bash
chmod +x RUN_V272_EVERYTHING.command INSTALL_AND_START_V272.command V272_SAFE_LAUNCHER.sh
./RUN_V272_EVERYTHING.command
```

The one-shot command installs dependencies, runs 27 authority tests in isolated
Python interpreters, records one public snapshot, applies the continuity gate,
verifies outputs, and builds:

```text
runtime/V272_Actual_Inverse_Handoff.zip
```

For persistent macOS collection and automatic verified daily audits after the
data gate becomes ready:

```bash
./INSTALL_AND_START_V272.command
```

The installer creates a LaunchAgent with `RunAtLoad=true` and `KeepAlive=true`.
It does not use `StartInterval`.

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
registered taker fee. Inverse option premiums and fees are calculated in BTC and
converted to USD at the contemporaneous index.

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

## Verification

The 27 authority tests include:

- inverse-contract P&L identities;
- perpetual bid/ask sensitivity of final equity;
- actual funding sensitivity of final equity;
- held-option state and quote-continuity gates;
- ready-true end-to-end economic execution;
- nano-dollar ledger identity;
- pre-trade initial-equity baseline;
- structured-metric report generation;
- deterministic input and output manifests.

Every authority test runs in a fresh Python interpreter. The sanitized artifact
is then tested again from its own clean directory before the deterministic ZIP
is uploaded.

## Boundaries

V27.2.1 evaluates one frozen ATM long-straddle plus inverse-perpetual delta hedge.
It does not guarantee future profit or claim that all options strategies are
impossible. Any historical pass is capped at `NEEDS_NEW_OOS`.
