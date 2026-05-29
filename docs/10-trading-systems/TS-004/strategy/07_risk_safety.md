# 07 Risk and Safety

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Hard risk limits

These limits are non-negotiable. Override requires Change Control process.

| Limit | Value | Scope |
|---|---|---|
| Max risk per trade (% account equity) | 0.50% | Per signal |
| Max open positions simultaneously | 1 | Per system |
| Max daily loss (% account equity) | 1.50% | Rolling calendar day |
| Max drawdown from peak before system pause | 15.00% | Rolling from peak equity |
| Max consecutive losses before manual review | 4 | Consecutive closed losses |
| Max position size | 0.10 lots (micro) | Hard ceiling regardless of Kelly |
| Minimum position size | 0.01 lots | Do not scale below micro |

## Stop loss specification

| Parameter | Value | Notes |
|---|---|---|
| Stop type | ATR multiple | Dynamic to current volatility |
| Stop distance | 1.5 × ATR14 from entry | Computed at bar close (entry bar) |
| Stop placement | Price direction (long: entry − stop_dist; short: entry + stop_dist) | |
| Stop modification after entry | Not allowed | Stops are set-and-hold |
| Trailing stop | Not used in v1 | Deferred to micro-live phase |

**ATR14 at H4:** Typical EURUSD H4 ATR14 ≈ 25–45 pips (1.5× = 37–67 pip stops). This is appropriate for H4 event-continuation holds of 40+ hours.

## Take profit specification

| Parameter | Value | Notes |
|---|---|---|
| Take profit type | Time-based (horizon exit) | Hold for up to 10 bars |
| Time-based exit | Close at bar close +10 if stop not hit | |
| Fixed TP | Not used in v1 | |
| Partial profit | Not used in v1 | |

## Circuit breaker specification

Implemented using `training/circuit_breaker.py` (P3):

| Parameter | Value |
|---|---|
| `max_daily_loss_pct` | 0.015 (1.5%) |
| `max_drawdown_pct` | 0.15 (15%) |
| `max_consecutive_losses` | 4 |
| `cooldown_bars` | 20 H4 bars (= 80 hours = ~3.5 trading days) |

**Behaviour on trip:**
- Circuit breaker is tripped: EA does not enter new positions.
- Existing positions: closed at next available price.
- Cooldown: 20 bars of silence before resumption.
- Manual reset required after drawdown trip (automated reset only after daily-loss trip).

**Monitoring integration:**
- Circuit breaker state published to Prometheus gauge `ts004_circuit_breaker_status`.
- Alert rule: `ts004_circuit_breaker_status == 1` for > 0 minutes → page.

## Position sizing (live phase)

For live deployment after promotion:

| Formula | Value |
|---|---|
| Kelly fraction | `kelly_fraction(win_rate, avg_win, avg_loss)` from `training/portfolio_sizing.py` |
| Half-Kelly factor | 0.5 (risk-adjusted scale-in) |
| Risk amount per trade | `half_kelly_fraction × account_equity × max_risk_pct` |
| Lot size | `risk_amount / (stop_distance_pips × pip_value)` |
| Max lot size cap | 0.10 lots |

Discovery phase: fixed 0.01 lots. Kelly not applied until micro-live after promotion.

## Safety checks in EA (pre-entry)

Before each entry, the EA must check:

| Check | Action if fails |
|---|---|
| Backend API reachable | Fail closed — do not enter |
| Signal probability ≥ threshold | Skip signal |
| Volatility regime in [0.80, 2.00] | Skip signal |
| Spread < 2.5 pips | Skip signal |
| Daily loss < 1.5% of equity | Skip signal (circuit breaker) |
| Drawdown < 15% from peak | Skip signal (circuit breaker) |
| No existing open position | Skip (single position policy) |
| Market not closed (weekend / holiday) | Skip |

## Risk documentation

- Risk limits reviewed: per live phase milestone
- Risk limit breach logging: `ts004_risk_event` metric in Prometheus
- Incident escalation: see [10_incident_runbook.md](10_incident_runbook.md)
