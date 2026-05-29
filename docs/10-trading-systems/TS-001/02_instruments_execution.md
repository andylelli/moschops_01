# 02 Instruments and Execution Profile

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Instrument universe
1. Primary symbol: EURUSD.
2. Intended near-term expansion: major FX pairs with proven metadata and spread quality.
3. Exclusions: illiquid symbols and symbols with unstable execution quality.

## Timeframe policy
1. Live decision timeframe: D1.
2. Test-only mode supports shorter timeframes for integration verification.
3. Test-mode outcomes are not accepted as promotion evidence.

## Execution assumptions
1. Execution path: MT5 EA sends payload to backend signal/risk flow and places orders via CTrade.
2. Decision-time spread checked in pips before order attempts.
3. Daily loss guard blocks new entries when breached.

## Venue constraints
1. Lot validation: broker min, max, and step must be respected.
2. Margin check: trade blocked if margin constraints fail.
3. Trade mode check: blocked for disabled or close-only symbols.

## Execution failure policy
1. Backend request failure: no new entry and error logged in terminal output.
2. Invalid response path: treated as non-tradable state for entry attempts.
3. Protective behavior: exits and safety maintenance remain available.

## Current known simplifications
1. Strategy-level cost stress assumptions are still mostly validation-side and need stronger runtime integration for promotion.
2. Full partial-fill and requote simulation remains a planned enhancement.
