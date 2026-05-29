# 09 Live Operations

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Deployment stages

| Stage | Prerequisites | Duration |
|---|---|---|
| Discovery | None | Until holdout pass |
| Paper trading | Gates B + C passed (holdout) | ≥ 30 days |
| Micro-live | Gates B + C + D + E passed | Until 50+ live trades |
| Full live | All gates passed + micro-live profitability confirmed | Ongoing |

## Current stage

**Discovery.** No paper trading or live deployment active.

## Deployment topology

| Component | Environment | Notes |
|---|---|---|
| Backend API | `localhost:3000` (local) / Docker container | Signal delivery and logging |
| PostgreSQL | Docker container (port 5432) | Signal and outcome storage |
| ONNX inference | Loaded by backend on startup | From `models/ts004_v1.onnx` |
| MetaTrader 5 | Windows desktop / VPS | EA polling backend API |
| Prometheus / Grafana | Sidecar (docker-compose) | Monitoring |

## Model deployment procedure

1. Confirm locked holdout run artefacts are in `docs/09-training-runs/runs/<run_dir>/`.
2. Copy `artifacts/model.onnx` to `models/ts004_v1.onnx`.
3. Copy `artifacts/scaler.pkl` to `models/scaler_ts004_v1.pkl`.
4. Update backend inference loader to reference new model path.
5. Restart backend service: `scripts/start-backend-prod.bat`.
6. Verify inference endpoint: `GET http://localhost:3000/api/v1/signal?symbol=EURUSD&timeframe=H4`.
7. Check health endpoint: `GET http://localhost:3000/healthz`.
8. Attach EA to EURUSD H4 chart in MetaTrader 5.
9. Run `scripts/check-local-health.bat` to confirm full stack operational.

## Signal delivery SLO

| Metric | Target |
|---|---|
| Signal delivery latency | < 200 ms (P95) |
| Backend API latency | < 100 ms (P95) |
| Signal completeness | 100% of H4 bar closes within 60 seconds |
| Backend uptime | ≥ 99.5% during trading hours |

## Monitoring dashboard

Grafana panels required for TS-004:

| Panel | Metric source | Notes |
|---|---|---|
| Signal probability histogram | Prometheus `ts004_signal_prob` | Detect distribution shift |
| Trade PnL over time | PostgreSQL query | Outcome tracking |
| Circuit breaker status | `ts004_circuit_breaker_status` | Alert on trip |
| Inference latency | `ts004_inference_latency_ms` | SLO check |
| Feature distribution (vol_regime) | `ts004_vol_regime_value` | Regime shift detection |
| Signal count per day | `ts004_signals_total` | Activity monitor |

## Live monitoring rules

| Condition | Action |
|---|---|
| Signal probability distribution shifts by > 10% vs. baseline | Investigate; flag for retrain |
| vol_regime consistently outside gate bounds for > 5 days | Review gate bounds; do not retrain |
| Win rate falls below 40% for 10+ consecutive signals | Review circuit breaker; consider system pause |
| Backend latency P95 > 300 ms for > 1 hour | Page on-call; investigate infrastructure |
| No signals for > 3 days (circuit breaker not tripped) | Check EA and backend connectivity |

## Shadow trader (paper phase)

Use `training/shadow_trader.py` (P3) throughout paper phase:

```python
from training.shadow_trader import ShadowTrader
trader = ShadowTrader(output_dir="docs/09-training-runs/shadow/TS-004", threshold=0.62)
trader.log_signal(bar_time_utc=bar_time, signal_prob=prob)
# On outcome:
trader.mark_outcome(bar_time_utc=bar_time, actual_return=return_bps)
report = trader.performance_report()
trader.save()
```

Shadow trader log: `docs/09-training-runs/shadow/TS-004/shadow_trades.json`.
Shadow report reviewed weekly during paper phase.
