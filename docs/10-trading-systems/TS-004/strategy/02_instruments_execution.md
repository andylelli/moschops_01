# 02 Instruments and Execution

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Instrument specification

| Field | Value |
|---|---|
| Symbol | EURUSD |
| Asset class | FX major |
| Timeframe | H4 |
| Session coverage | 24/5 (Monday 00:00 – Friday 22:00 UTC) |
| Tick value (standard lot) | $10 per pip ($1 per pip per 0.10 lot) |
| Minimum trade size | 0.01 lots (micro) |
| Contract size | 100,000 units |
| Typical spread (normal session) | 0.5–1.0 pips |
| Typical spread (news event) | 3–8 pips |
| Overnight swap rates | As per broker schedule |

## Execution platform

| Field | Value |
|---|---|
| Platform | MetaTrader 5 |
| EA framework | Existing MQL5 EA template |
| Order type | Market orders at bar close |
| Order placement | On bar close (not at open of next bar) |
| Signal provider | Backend API (localhost:3000) |

## Execution constraints

| Constraint | Value | Rationale |
|---|---|---|
| Max slippage tolerance | 2 pips | Reject execution if slippage exceeds limit |
| Re-quote policy | Cancel and wait for next bar | Do not chase price |
| Maximum spread to enter | 2.5 pips | Do not enter if spread > 2.5 pips |
| News blackout window | Optional — see note below | Regime gate acts as implicit news filter |
| Session filter | None required | Regime gate filters event noise |

**Note on news blackout:** The volatility regime gate (vol_regime > 2.00) acts as an implicit news blackout. A separate calendar-based blackout is not required in v1. If the gate fails to filter high-spread entries in practice, add a spread check at order time.

## Broker requirements

| Requirement | Reason |
|---|---|
| Raw spread account | Ensure spread + commission cost model is accurate |
| FIFO / no hedging | Single position policy |
| EA autotrading allowed | Required for signal execution |
| Minimum margin: 1:30 leverage | Micro-lot position at 0.01 lots requires ~$33 margin |

## Cost model

| Cost component | Assumption | Stress assumption |
|---|---|---|
| Spread | 2.5 bps (per round trip half) | 5.0 bps (2×) |
| Commission | 1.0 bps | 2.0 bps |
| Slippage | 0.5 bps | 1.5 bps (3×) |
| Overnight swap | 0.5 bps / night × avg 2 nights | 1.5 bps per hold |
| Total base | ~4.5 bps per trade | ~10.0 bps per trade |

## Lot sizing (discovery phase)

| Phase | Lot size policy |
|---|---|
| Discovery (all experiments) | Fixed 0.01 lots |
| Paper trading | Fixed 0.01 lots (notional tracking only) |
| Micro-live | Dynamic — position_size = kelly × 0.5 × account_equity / (stop_distance × pip_value) |
| Full live | To be defined at promotion |

## EURUSD specific risks

| Risk | Mitigation |
|---|---|
| Event-driven gap | Regime gate blocks entries during elevated vol |
| Liquidity reduction (week open) | Consider filtering first bar of week (optional EXP) |
| Correlation with DXY | Monitor regime correlation if adding USD pairs later |
| Summer / holiday low liquidity | Regime gate naturally reduces entries in low-vol periods |
