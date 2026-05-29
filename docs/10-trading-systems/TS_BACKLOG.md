# Trading Systems Backlog

Version: 1.0
Last updated: 2026-05-27
Status: Active

## Backlog Rules
1. Every idea needs a clear market thesis.
2. Every idea must declare instrument/timeframe scope up front.
3. Prioritize systems with low dependency overlap and clear differentiation from TS-001.

## Candidate Systems
| ID | Name | Thesis | Instruments | Timeframe | AI Role | Priority | Status |
|---|---|---|---|---|---|---|---|
| TS-002 | Mean-Reversion Volatility Compression | Short-term overextension tends to mean-revert after volatility spikes | FX majors | H1/H4 | Entry quality filter | High | In discovery |
| TS-003 | Cross-Asset Momentum Rotation | Relative-strength persistence across instrument basket | FX + indices | H4 | Ranking and allocation support | High | In discovery |
| TS-004 | Event-Aware Trend Continuation | Post-event trend continuation after volatility normalization | EURUSD | H4 | Event-risk gating and sizing | Medium | Discovery |
| TS-005 | Regime-Switch Breakout | Different breakout logic per regime state | FX majors | D1 | Regime classifier | Medium | Proposed |

## Intake Checklist For New TS
1. Why this strategy may have durable edge.
2. Why this is not a duplicate of existing TS.
3. What failure regimes are expected.
4. What data is required and currently available.
5. What minimum experiment budget is needed.

## Next Actions
1. Finalize TS-002 data contract and feature schema drafts.
2. Implement intraday-capable historical provider path (H1/H4 coverage) before further TS-003 H4 experiments.
3. Re-run TS-003 EXP-001 baseline immediately after intraday provider is available.
