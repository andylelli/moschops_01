# 11 Experiment Log

System ID: TS-003

## Experiment entries
| Date | Experiment ID | Hypothesis | Single change made | Result | Decision |
|---|---|---|---|---|---|
| 2026-05-27 | EXP-001 | H4 momentum baseline can produce positive post-cost expectancy with acceptable DD under fail-closed gating | Baseline H4 run with default TS-003 threshold grid | Blocked: 0 H4 bars fetched from provider (EURUSD, SPY, QQQ, DIA probes) | INVALID_FOR_PROMOTION |
| 2026-05-27 | EXP-002 | With full H4 history and calibrated threshold band, model should produce a non-degenerate baseline suitable for subsequent feature iteration | Fixed intraday timestamp parsing in historical ingestion; trained H4 baseline (`horizon=6`, `wf=6`, `emb=5`, grid `0.40..0.55`, constraints `DD<=15`, median trades >=20) | Trained baseline produced, but holdout quality weak (very low predicted positive rate, negative post-cost net return) | Continue with redesign |
| 2026-05-27 | EXP-003 | Restricting threshold range away from sparse regime may recover actionable trade flow for H4 | Trained full-window H4 baseline with `horizon=6`, `wf=6`, `emb=5`, grid `0.40,0.45,0.50`, constraints `DD<=35`, median trades >=120 | Trade-active output achieved (933 trades, +1.30% post-cost net return), but max DD -35.31% violates TS-003 risk target | Continue with redesign |
| 2026-05-27 | EXP-004 | Regime gating and anti-degenerate threshold fallback should prevent curve-fit/no-trade selection while preserving fail-closed policy | Added fallback median-trades floor and regime gate in trainer; reran TS-003 H4 9-config dev sweep under hard constraints `DD<=15`, median trades >=120 with holdout blocked unless feasible | Blocked by policy: 0/9 feasible dev configs in rerun `2026-05-27_21-37-ts003-h4-lab`; all deterministic gate decisions `REJECT` (`data=true`, `stat=false`, `risk=false`) | Continue with redesign |
| 2026-05-27 | EXP-005 | Explicit signal redesign (trend-follow and regime-split mean-reversion) may improve robustness versus threshold-only tuning | Implemented signal variants in trainer and ran strict two-variant H4 sweep (18 dev runs total) with unchanged hard constraints `DD<=15`, median trades >=120, fail-closed holdout block | Blocked by policy: 0/18 feasible dev configs (`2026-05-27_21-41-ts003-h4-lab`); trend-follow mostly runtime-filter sparse, regime-split active but statistically/risk-gate failing; all gate decisions `REJECT` | Continue with redesign |
| 2026-05-27 | EXP-006 | Cost-aware edge objective should improve robustness by training on minimum expected edge rather than raw direction | Added trainer label objective mode (`edge`, `minEdgeBps=8`) and reran strict two-variant H4 sweep (18 dev runs) under unchanged hard constraints `DD<=15`, median trades >=120 | Blocked by policy: 0/18 feasible dev configs in `2026-05-27_21-45-ts003-h4-lab`; runtime stability improved, but statistical/risk gates still fail and trade counts remain far below requirement | Continue with redesign |
| 2026-05-27 | EXP-007 | Feasibility-gap diagnostics should make structural gate mismatch explicit and prevent repeated blind reruns | Added blocker diagnostics summarizing max observed trades/net/DD per variant and reran strict two-variant edge-objective sweep | Blocked by policy in `2026-05-27_21-47-ts003-h4-lab`; diagnostics show max observed trades `63` (trend-follow) and `40` (regime-split) vs target median trades `120`, confirming structural activity shortfall | Redefine signal/activity design before rerun |

## Required fields per entry
1. Pre-registered hypothesis.
2. Exact config diff versus prior run.
3. Train/validation/holdout windows used.
4. Trial count to date.
5. Links to artifacts and report.

## Integrity rules
1. No deletion of failed experiments.
2. No undocumented reruns.
3. Mark invalid runs explicitly.
4. If no feasible dev configuration exists, holdout is blocked by policy.

## Notes
1. Baseline run attempted at `docs/09-training-runs/runs/2026-05-27_21-20-ts003-h4-baseline/artifacts` failed before report generation because training fetch returned zero bars.
2. Immediate prerequisite for TS-003 H4 execution: enable an intraday-capable provider route in backend historical download path.
3. Parser fix enabling intraday ingestion was implemented in `backend/src/services/historical-data.ts`; fixed baseline artifacts at `docs/09-training-runs/runs/2026-05-27_21-36-ts003-h4-trained-baseline-fixed/artifacts`.
4. Trade-active comparison artifacts are at `docs/09-training-runs/runs/2026-05-27_21-40-ts003-h4-trained-active/artifacts`.
5. Anti-curve-fit gated lab artifacts are at `docs/09-training-runs/runs/2026-05-27_21-37-ts003-h4-lab/`; blocker file is `selection_blocker.json` and deterministic gate outcomes are included in `summary.csv`.
6. Per-run deterministic gate evaluation files are generated automatically at `Rxx-dev/artifacts/ts003_gate_evaluation.json` using `scripts/evaluate-ts003-gates.ps1`.
7. Two-variant redesign sweep artifacts are at `docs/09-training-runs/runs/2026-05-27_21-41-ts003-h4-lab/`; variant-level outcomes and runtime failures are captured in `summary.csv` (`variant`, `selectionMode`, `error` columns).
8. Edge-objective rerun artifacts are at `docs/09-training-runs/runs/2026-05-27_21-45-ts003-h4-lab/`; `summary.csv` shows improved sweep stability but no feasible run under hard constraints.
9. Feasibility-gap diagnostics are included in blocker artifacts from `docs/09-training-runs/runs/2026-05-27_21-47-ts003-h4-lab/selection_blocker.json` under `feasibilityGapDiagnostics`.

