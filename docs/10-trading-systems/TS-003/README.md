# TS-003: Cross-Asset Momentum Rotation

Version: 0.1
Last updated: 2026-05-27
Status: In discovery
Owner: Trading + AI Engineering

## 1) System Summary
TS-003 targets relative-strength persistence across a basket, with rotation into stronger instruments and explicit risk throttling.

Primary objective:
1. Demonstrate positive post-cost out-of-sample expectancy with H4 decision cadence.
2. Keep acceptance drawdown within a hard ceiling of -15%.
3. Produce stable results across folds/regimes with full lineage.

## 2) Scope
1. Instrument universe: FX majors plus selected indices (phase 1 focuses on EURUSD for runner parity).
2. Primary timeframe: H4.
3. Secondary timeframe: D1 context filters only.

## 3) Initial Plan
1. Build H4 baseline run for EURUSD using existing historical split runner.
2. Finalize TS-003 data contract and feature schema for relative-strength signals.
3. Run first three pre-registered experiments under fail-closed policy.

## 4) Document Map
1. [_INDEX.md](_INDEX.md)
2. [00_system_charter.md](00_system_charter.md)
3. [01_strategy_spec.md](01_strategy_spec.md)
4. [06_validation_protocol.md](06_validation_protocol.md)
5. [08_promotion_gates.md](08_promotion_gates.md)
6. [11_experiment_log.md](11_experiment_log.md)
