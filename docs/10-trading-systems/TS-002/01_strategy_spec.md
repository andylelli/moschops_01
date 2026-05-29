# 01 Strategy Specification

System ID: TS-002

## Strategy thesis
Volatility spikes and short-term directional overextension in major FX pairs are often followed by partial reversion as liquidity normalizes. TS-002 seeks that reversion only when expansion transitions into compression.

## Entry logic
1. Compute expansion state using normalized ATR and return z-score on H1.
2. Permit long setup when downside overextension exceeds threshold, then compression confirmation appears within a bounded lookahead window.
3. Permit short setup symmetrically for upside overextension with compression confirmation.
4. Reject entries if spread, slippage estimate, or cooldown guard is violated.

## Exit logic
1. Exit at mean-reversion target when price returns to mid-band proxy.
2. Time-stop exit if reversion does not progress within max holding bars.
3. Early abort exit if post-entry volatility re-expands against position.

## Stop logic
1. Initial stop uses ATR multiple anchored at entry timeframe.
2. Optional break-even stop after minimum favorable excursion.
3. Hard kill for abnormal gap/slippage beyond configured guard.

## Position sizing logic
1. Base risk per trade fixed in discovery (small risk budget).
2. Volatility-adjusted size scaling with hard max size cap.
3. No pyramiding while in discovery.

## Parameter table
| Parameter | Type | Default | Range | Effect |
|---|---|---|---|---|
| expansionZ | float | 1.8 | 1.2-2.8 | Higher means fewer but cleaner overextension candidates |
| compressionLookaheadBars | int | 4 | 2-8 | Window to wait for compression confirmation |
| meanReversionTargetAtr | float | 0.8 | 0.4-1.4 | Profit target distance proxy |
| stopAtr | float | 1.2 | 0.8-2.0 | Initial stop distance |
| maxHoldBars | int | 12 | 4-24 | Time stop horizon |
| cooldownBars | int | 6 | 0-24 | Post-loss pause to prevent clustering |

## Regime assumptions
1. Performs best when volatility spikes revert inside range-bound or transition regimes.
2. Performs worst when persistent directional trends continue after spike without reversion.

## Known invalid market states
1. Major scheduled macro events with structurally wide spreads and jump risk.
2. Thin-liquidity sessions where execution costs dominate mean-reversion edge.

