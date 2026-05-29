# 10 Incident Runbook

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## Severity definitions

| Severity | Definition | Response time |
|---|---|---|
| P1 — Critical | Positions open with no stop; backend unreachable with EA running live; data corruption | Immediate (< 15 min) |
| P2 — High | Circuit breaker tripped; signal delivery failure for > 30 min; abnormal position sizing | < 1 hour |
| P3 — Medium | Win rate degradation; feature distribution shift; elevated latency | < 24 hours |
| P4 — Low | Monitoring gap; documentation discrepancy; non-critical config mismatch | < 1 week |

## Runbook: Backend API unreachable (P1)

**Symptoms:** EA not receiving signals; health check fails; `GET /healthz` timeout or 5xx.

**Steps:**
1. Open `scripts/check-local-health.bat` — check Docker container status.
2. Run `docker ps` to confirm backend and DB containers are running.
3. Check backend logs: `docker logs moschops_backend`.
4. If container crashed: restart with `scripts/start-backend-prod.bat`.
5. If DB connection failed: restart DB with `scripts/start-db.bat`.
6. Verify inference model loaded: `GET /api/v1/signal` returns valid JSON.
7. EA will resume automatically when backend is reachable (fail-closed handles the gap).
8. Log incident in `11_experiment_log.md` if this occurred during paper trading.

## Runbook: Circuit breaker tripped (P2)

**Symptoms:** `ts004_circuit_breaker_status == 1` Grafana alert; EA no longer entering positions.

**Steps:**
1. Do NOT manually reset until root cause is investigated.
2. Check last N closed trades for anomalous PnL pattern (spike, gap, abnormal spread).
3. Check Grafana for vol_regime values during the loss period — was the gate functioning?
4. If losses were within expected risk parameters: let cooldown elapse naturally (20 bars).
5. If losses suggest system malfunction (e.g., wrong model version, config error): pause EA manually and investigate.
6. After cooldown: call `circuit_breaker.reset_daily()` if daily trigger; only call `reset_all()` after full investigation.
7. Document cause and resolution in `11_experiment_log.md`.

## Runbook: Signal probability distribution shift (P3)

**Symptoms:** Grafana histogram of `ts004_signal_prob` shifted > 10% from baseline distribution; signal count significantly above or below historical average.

**Steps:**
1. Export recent `ts004_signal_prob` values from Prometheus.
2. Compare distribution statistics (mean, std, quantiles) to training-time calibration report.
3. Check vol_regime values — sustained regime shift can cause legitimate distribution change.
4. If distribution shift is large and persistent (> 5 days): flag for retrain review.
5. Check `training/retrain_pipeline.py` `should_retrain()` output with current monitoring alert.
6. Do NOT retrain without completing Change Control process.

## Runbook: Position open at session close (P1 — data corruption risk)

**Symptoms:** EA holds position over Friday close or public holiday weekend; unusual gap risk.

**Steps:**
1. Review position: if in profit > 10 bps, let stand with stop in place.
2. If near stop or in loss: close manually before session end.
3. Ensure EA session-filter code is active (check EA parameters in MT5).
4. Log any manual intervention in `11_experiment_log.md`.

## Runbook: Model version mismatch (P2)

**Symptoms:** Backend serving a different model version than what is documented; feature schema mismatch; unexpected signal patterns.

**Steps:**
1. Check backend model path config: confirm it points to `models/ts004_v1.onnx`.
2. Verify ONNX model metadata version matches documented version in `05_model_training.md`.
3. Check `models/feature_schema_ts004_v1.json` matches `04_feature_schema.md`.
4. If mismatch: take backend offline; correct model deployment; restart; re-verify.
5. Document in `12_change_control.md`.

## On-call contacts

| Role | Action for P1/P2 |
|---|---|
| Trading team | Manually close positions if EA cannot be stopped |
| AI Engineering | Backend and model investigations |
| DevOps | Infrastructure and container issues |

## Post-incident process

After every P1 or P2 incident:
1. Write a post-incident summary in `11_experiment_log.md` (mark as INC type, not EXP).
2. Identify root cause: code, infrastructure, market, or human error.
3. Add preventive action to `12_change_control.md`.
4. Update monitoring rules in `09_live_operations.md` if detection gap identified.
