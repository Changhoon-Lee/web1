# V27.2.4 Deribit Public WebSocket Authority

V27.2.4 replaces the diagnostic sequential REST recorder with one continuous,
unauthenticated Deribit WebSocket market-data connection.

## One command on macOS

```bash
chmod +x INSTALL_AND_START_V2724.command
./INSTALL_AND_START_V2724.command
```

The installer:

1. verifies all 45 authority tests in fresh Python interpreters;
2. stops and backs up `com.zcode.v272free.recorder` from V27.2.3;
3. installs under `~/Library/Application Support/V2724Free/`;
4. registers `com.zcode.v2724free.recorder` with `RunAtLoad` and `KeepAlive`;
5. starts the public WebSocket recorder.

## Public data paths

Real-time data:

```text
wss://www.deribit.com/ws/api/v2
public/subscribe
ticker.<instrument>.agg2
instrument.state.option.BTC
```

REST is allowed only for initial and hourly `public/get_instruments`
reconciliation. `public/ticker`, book-summary polling, credentials, paid data,
and historical interpolation are forbidden in continuous authority mode.

## Universe

```text
Entry universe:       BTC options, 21–45 DTE
Collection universe:  BTC options, 7–45 DTE
Strikes:              all
Option types:         call and put
Hedge:                BTC-PERPETUAL
```

The wider collection range ensures a contract entered at 21 DTE remains
recorded through the 7 DTE exit boundary.

## Same-cutoff snapshot

The client continuously retains per-symbol exchange-timestamped ticker states.
At each UTC five-minute boundary it freezes, for every eligible symbol, the
latest message whose exchange timestamp is less than or equal to that cutoff.
A message arriving later with a timestamp after the cutoff belongs only to a
future snapshot.

Each row includes:

```text
snapshot_target_timestamp
snapshot_frozen_at
source_timestamp
source_age_seconds
connection_epoch
subscription_epoch
authority
failure_reason
```

No snapshot can be authoritative after a reconnect until every current option
symbol and BTC-PERPETUAL have supplied a fresh ticker on the new connection.

## Fail-closed gates

Before economic metrics are allowed:

```text
90 active days
complete-day density p10 >= 80%
snapshot authority ratio >= 99%
option symbol coverage >= 99%
option quote coverage >= 99%
option actual-delta coverage >= 99%
BTC-PERPETUAL quote coverage = 100%
funding_8h coverage = 100%
median source age <= 5 seconds
p99 source age <= 30 seconds
maximum source age <= 60 seconds
```

The inverse accounting core additionally verifies actual deltas for every live
held option leg. A Black-Scholes fallback may appear in diagnostics but cannot
make the authority gate pass.

## Current expected state

Until all history gates pass:

```text
FREE_OPEN_DATA_CONTINUITY_NOT_READY
```

No Sharpe or CAGR is emitted before that point. The 90-day authority clock
starts on the first complete UTC day collected by V27.2.4. V27.2.3 REST data is
preserved only as a diagnostic control.
