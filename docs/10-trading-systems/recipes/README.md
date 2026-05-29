# Trading System Recipes

Version: 1.0
Last updated: 2026-05-28
Audience: Strategy designer, researcher

---

## Purpose

A **recipe** is the upstream design decision record created *before* any TS documentation is written. It captures the strategy thesis, every palette dimension selection, and the experiment plan that will drive all downstream documentation.

Without a signed-off recipe, no TS-00n folder may be created.

---

## What Problem This Solves

Previously, creating a new trading system meant copying 16 templates and filling them in cold — with no structured step to decide *what the strategy actually is* before writing documentation about it. Recipes enforce a design-first discipline:

```
Backlog idea  -->  Recipe (design decisions)  -->  TS folder (documentation)  -->  Lab
```

The recipe is the bridge. It is small enough to complete in one sitting, but captures enough to drive every template automatically.

---

## Full End-to-End Process

### Step 1 — Backlog intake
Ensure the strategy idea has an entry in [../TS_BACKLOG.md](../TS_BACKLOG.md) with:
- A one-line thesis
- Instrument / timeframe scope
- Why it is not a duplicate of an existing TS

### Step 2 — Assign a TS ID and recipe number
Pick the next available TS-00n ID from the catalogue in [../README.md](../README.md).
Assign the next sequential recipe number from the list below.

| Recipe file | TS ID | System name | Status |
|---|---|---|---|
| *(none yet — add as you create)* | | | |

### Step 3 — Copy the recipe skeleton
Copy [00_recipe_template.md](00_recipe_template.md) and rename it:

```
nn-recipe-ts-xxx.md   (e.g. 04-recipe-ts-004.md)
```

Save it in this folder (`recipes/`). It stays here permanently as the design record.

### Step 4 — Run the AI-guided design interview
Open [00_copilot_prompt.md](00_copilot_prompt.md), copy the prompt into a Copilot chat session, and follow the interview process. Copilot will guide you through all 11 design palette dimensions and help you fill in the recipe file.

Palette references used during the interview:
- [../../11-trading-tools/strategy-design-palette.md](../../11-trading-tools/strategy-design-palette.md) — current available options
- [../../11-trading-tools/future-design-palette.md](../../11-trading-tools/future-design-palette.md) — not-yet-implemented options (flag as backlog, do not use in recipe)

### Step 5 — Review and sign off the recipe
Before proceeding:
- All 11 design dimensions must have explicit selections (no blanks)
- The experiment plan section must have at least one hypothesis and proposed lab windows
- The risk constraints section must be complete
- The recipe owner must sign off with name and date

A recipe with any empty required field is NOT signed off.

### Step 6 — Create the TS folder
With a signed-off recipe in hand, use the second phase of [00_copilot_prompt.md](00_copilot_prompt.md) to generate the full TS-00n folder. Copilot will populate all 16 template documents from the recipe decisions.

### Step 7 — Register the system
Add the new system to the catalogue table in [../README.md](../README.md) with status `In discovery`.

### Step 8 — Run the lab
Execute experiments as specified in the recipe. Track all runs in `11_experiment_log.md`. Follow the lab operating model in [../LAB_OPERATING_MODEL.md](../LAB_OPERATING_MODEL.md).

### Step 9 — Gate evaluation
Gate evidence accumulates in `08_promotion_gates.md`. Promotion requires all gates passed — no exceptions.

---

## Governance Rules

1. A TS-00n folder must not be created before its recipe is signed off.
2. Recipe files are permanent records and must not be modified after sign-off without a change control note added to the recipe.
3. If design decisions change materially after a TS folder has been created, raise a new entry in `12_change_control.md` and note the change in the recipe file under a `## Amendments` section.
4. The palette selections in the recipe are the single source of truth for what the strategy was designed to do. Any divergence between recipe and actual implementation must be documented and justified.

---

## Folder Contents

| File | Purpose |
|---|---|
| README.md (this file) | Process overview, conventions, and governance rules |
| 00_recipe_template.md | Blank skeleton — copy for every new system |
| 00_copilot_prompt.md | AI prompt for Phase 1 (recipe) and Phase 2 (TS folder generation) |

Completed recipe files (`nn-recipe-ts-xxx.md`) accumulate here as systems are designed.
