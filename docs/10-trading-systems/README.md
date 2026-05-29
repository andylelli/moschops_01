# Trading Systems Catalogue

Version: 1.1
Last updated: 2026-05-28
Status: Active

## Purpose
Maintain a governed catalogue of trading systems so each strategy is documented, testable, and promotable without curve fitting.

## Lab Control Center
1. [LAB_OPERATING_MODEL.md](LAB_OPERATING_MODEL.md)
2. [TS_BACKLOG.md](TS_BACKLOG.md)
3. [LAB_SCOREBOARD.md](LAB_SCOREBOARD.md)
4. [recipes/README.md](recipes/README.md) — design recipes (mandatory before creating any TS folder)

All systems in this catalogue must comply with:
- [robust_trading_no_curve_fit_plan.md](robust_trading_no_curve_fit_plan.md)

## Catalogue
| ID | System Name | Instruments | Timeframe | AI Role | Status | Document |
|---|---|---|---|---|---|---|
| TS-001 | AI-Filtered Daily Breakout | FX majors (initial: EURUSD) | D1 | Setup quality filter + confidence gating | In discovery | [TS-001/README.md](TS-001/README.md) |
| TS-002 | Mean-Reversion Volatility Compression | FX majors (initial: EURUSD) | H1/H4 | Entry quality filter + compression confirmation | In discovery | [TS-002/README.md](TS-002/README.md) |
| TS-003 | Cross-Asset Momentum Rotation | FX majors + indices (phase 1 EURUSD) | H4 | Ranking and allocation support | In discovery | [TS-003/README.md](TS-003/README.md) |

## Folder Structure Standard
1. One folder per trading system, for example TS-001, TS-002.
2. Shared reusable templates stored only in templates.
3. Strategy folder must contain its own README and folder index.

Example structure:
1. robust_trading_no_curve_fit_plan.md
2. TRADING_SYSTEM_TEMPLATE.md
3. templates/README.md
4. LAB_OPERATING_MODEL.md
5. TS_BACKLOG.md
6. LAB_SCOREBOARD.md
7. TS-001/README.md
8. TS-001/_INDEX.md
9. TS-002/README.md
10. TS-002/_INDEX.md
11. TS-003/README.md
12. TS-003/_INDEX.md

## Lifecycle States
- Proposed
- In discovery
- Paper-only
- Micro-live
- Controlled scale
- Retired

## Governance Rules
1. No strategy can be added without a complete system document.
2. No strategy can be promoted without gate evidence.
3. Any override requires explicit rationale in the strategy document and run report.
4. Any run that violates no-bending policy is invalid for promotion.

## Authoring Rules for New Systems

**A signed-off recipe is required before any TS folder may be created.** See [recipes/README.md](recipes/README.md) for the full process.

Summary workflow:
1. Add idea to [TS_BACKLOG.md](TS_BACKLOG.md).
2. Assign TS ID and create a recipe file in [recipes/](recipes/) using [recipes/00_recipe_template.md](recipes/00_recipe_template.md).
3. Complete the recipe using the AI-guided process in [recipes/00_copilot_prompt.md](recipes/00_copilot_prompt.md) Phase 1.
4. Sign off the recipe.
5. Generate the TS-00x folder from the signed-off recipe using [recipes/00_copilot_prompt.md](recipes/00_copilot_prompt.md) Phase 2.
6. Add TS-00x row to this catalogue table.
7. Run lab experiments as specified in the recipe.

Template references:
- [TRADING_SYSTEM_TEMPLATE.md](TRADING_SYSTEM_TEMPLATE.md)
- [templates/README.md](templates/README.md)

Required minimum for new entries:
1. Stable strategy ID and versioning policy.
2. Instrument and timeframe scope.
3. Full signal, risk, and execution logic.
4. AI feature schema and training/validation protocol.
5. Promotion gates and deployment ladder.
6. Audit and reproducibility requirements.
