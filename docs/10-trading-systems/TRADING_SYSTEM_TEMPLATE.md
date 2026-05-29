# Trading System Template Overview

Version: 1.2
Last updated: 2026-05-28
Status: Active

## Purpose
Use this file as a quick-start entrypoint. The full production-grade structure lives in the shared template pack under templates.

A recipe must be signed off before a TS folder is created. See [recipes/README.md](recipes/README.md) for the full design-first process.

## Recommended Workflow

### Phase 1 — Recipe (design decisions first)
1. Add the strategy idea to [TS_BACKLOG.md](TS_BACKLOG.md).
2. Copy [recipes/00_recipe_template.md](recipes/00_recipe_template.md) to `recipes/nn-recipe-ts-xxx.md`.
3. Use the Phase 1 prompt in [recipes/00_copilot_prompt.md](recipes/00_copilot_prompt.md) to run an AI-guided design interview covering all 11 palette dimensions.
4. Sign off the completed recipe.

### Phase 2 — TS Folder (documentation from recipe)
5. Use the Phase 2 prompt in [recipes/00_copilot_prompt.md](recipes/00_copilot_prompt.md) to generate all 16 template documents populated from the recipe.
6. Remove _TEMPLATE suffixes and verify all TS-XXX placeholders are replaced.
7. Complete required docs first, then optional docs.
8. Only promote after promotion gates are fully evidenced.

## Core References
1. [README.md](README.md)
2. [recipes/README.md](recipes/README.md)
3. [recipes/00_recipe_template.md](recipes/00_recipe_template.md)
4. [recipes/00_copilot_prompt.md](recipes/00_copilot_prompt.md)
5. [templates/README.md](templates/README.md)
6. [robust_trading_no_curve_fit_plan.md](robust_trading_no_curve_fit_plan.md)

## Minimum Required Documents
1. 00_system_charter
2. 01_strategy_spec
3. 03_data_contract
4. 04_feature_schema
5. 05_model_training
6. 06_validation_protocol
7. 07_risk_safety
8. 08_promotion_gates
9. 11_experiment_log
10. 13_audit_traceability
11. 14_document_completion_checklist

## Quick Skeleton For A New TS Folder
1. README.md
2. _INDEX.md
3. 00_system_charter.md
4. 01_strategy_spec.md
5. 03_data_contract.md
6. 04_feature_schema.md
7. 05_model_training.md
8. 06_validation_protocol.md
9. 07_risk_safety.md
10. 08_promotion_gates.md
11. 11_experiment_log.md
12. 13_audit_traceability.md
13. 14_document_completion_checklist.md
