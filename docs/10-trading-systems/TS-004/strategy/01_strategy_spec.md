# 01 Strategy Specification

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Signal logic overview

TS-004 generates long or short signals on EURUSD H4 when:
1. The volatility regime ratio is in the normalisation window [0.80, 2.00],
2. The classifier assigns a probability ≥ selected threshold (≥ 0.52 minimum), and
3. The price is aligned with the long-run trend direction (SMA200 filter).

All three conditions must be satisfied simultaneously for a valid entry.

## Signal flow

```
H4 bar closes
  → compute features (features.py build_feature_set)
  → compute volatility_regime = vol20 / vol100
  → REGIME GATE CHECK:
      if vol_regime < 0.80 OR vol_regime > 2.00 → BLOCK (no entry)
  → query ONNX model → P(edge) probability
  → THRESHOLD CHECK:
      if P < threshold → BLOCK
  → TREND DIRECTION CHECK:
      if long signal and close < SMA200 → BLOCK
      if short signal and close > SMA200 → BLOCK
  → ENTRY generated → logged to backend API
```

## Entry conditions

### Long entry (all required)
- `vol_regime` in [0.80, 2.00]
- `P(edge)` ≥ threshold (≥ 0.52 minimum)
- `close` > `SMA200`
- `trend_strength` ≥ 0.30

### Short entry (all required)
- `vol_regime` in [0.80, 2.00]
- `P(edge)` ≥ threshold (≥ 0.52 minimum)
- `close` < `SMA200`
- `trend_strength` ≤ −0.30

## Exit conditions

| Exit type | Condition | Priority |
|---|---|---|
| Stop loss | 1.5 × ATR14 from entry | 1 (highest) |
| Take profit | Not fixed; held for horizon bars | 2 |
| Time-based exit | Close at bar N+10 if stop not hit | 3 |
| Circuit breaker | Daily loss > 1.5% of account | 4 |

## Regime gate specification

| Parameter | Value | Notes |
|---|---|---|
| Gate metric | `vol20 / vol100` | vol20 = 20-bar realised vol, vol100 = 100-bar baseline |
| Lower bound | 0.80 | Below → market too quiet; no event catalyst |
| Upper bound | 2.00 | Above → event still active; spread risk elevated |
| Gate action | block-all | No entries outside the gate bounds |
| Gate review cadence | EXP-003 onwards | Re-evaluate bounds if trade count < 40 |

## Threshold selection protocol

| Parameter | Value |
|---|---|
| Selection method | constrained-optimisation |
| Dev window scoring metric | Net return (median across folds) |
| Hard minimum probability | 0.52 |
| Trade count floor | 60 (constrained optimisation constraint) |
| Drawdown ceiling | 20% (constrained optimisation constraint) |
| Holdout threshold lock | After dev phase is complete |

## Signal variants

| Variant ID | Description | Active? |
|---|---|---|
| trend-follow | Entries only in SMA200 direction | Yes (v1.0) |
| mean-reversion | Entries against trend at extremes | No (future) |
| event-calendar | Entries timed to event windows using calendar data | No (future) |

## Model and calibration

| Field | Value |
|---|---|
| Base estimator | XGBoost (`xgb`) |
| Output type | Calibrated probability P(edge) |
| Calibration method | Isotonic regression (cv=prefit) |
| Inference runtime | ONNX (exported after training) |
| Inference endpoint | `GET /api/v1/signal?symbol=EURUSD&timeframe=H4` |

## Position sizing (discovery phase)

| Parameter | Value |
|---|---|
| Position size | Fixed micro-lot (0.01) |
| Kelly fraction | Not applied in discovery; apply from EXP-005 onwards |
| Max simultaneous positions | 1 |
| Max correlation adjustment | N/A (single instrument) |
| Circuit breaker activation | 1.5% daily loss or 4 consecutive losses |

## Label definition

| Parameter | Value |
|---|---|
| Label mode | edge |
| Edge threshold | 8 bps |
| Horizon | 10 bars (H4) = ~40 hours |
| Positive class | `gross_return_H_bars > min_edge_bps / 10000` |
| Class balance | `class_weight='balanced'` |

## Linked documents

- Regime gate bounds → [04_feature_schema.md](04_feature_schema.md) for `vol_regime` definition
- Threshold selection → [06_validation_protocol.md](06_validation_protocol.md)
- Position sizing → [07_risk_safety.md](07_risk_safety.md)
- Gate thresholds → [08_promotion_gates.md](08_promotion_gates.md)
