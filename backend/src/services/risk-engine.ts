import type { RiskCheckRequest, RiskCheckResponse, SignalRequest } from "../types/contracts";
import { RISK_LIMITS } from "../config/riskLimits";

export interface RiskDecision {
  approved: boolean;
  reasonCodes: string[];
}

/**
 * Evaluate signal-level risk controls.
 *
 * Performs basic safety checks on individual trade signals before they reach
 * portfolio-level evaluation. All checks must pass for approval (fail-safe logic).
 *
 * @param input Signal evaluation request with market and account snapshots
 * @returns Risk decision indicating approval status and veto reason codes
 *
 * Constraints checked (any violation → VETOED):
 *
 * 1. **ATR Validity**: ATR > 0
 *    - Reason: ATR ≤ 0 indicates no volatility; market untradeable
 *    - Logged as: "INVALID_ATR"
 *
 * 2. **Spread Guard**: (spreadPrice / ATR) ≤ 20%
 *    - Reason: Wide spreads consume risk budget; 20% threshold prevents excessive slippage
 *    - Threshold Rationale: If ATR = 50 pips, allowed spread = 10 pips max
 *    - Source: docs/02-architecture/lld_v1.md § Signal-Level Risk § Spread Guard
 *    - Logged as: "SPREAD_TOO_WIDE"
 *
 * 3. **Open Trades Limit**: openTrades < 6
 *    - Reason: Limit correlation risk; prevent over-leveraging
 *    - Threshold Rationale: 6 positions enables diversification without resource exhaustion
 *    - Source: docs/02-architecture/lld_v1.md § Portfolio Limits § Max Open Trades
 *    - Logged as: "MAX_OPEN_TRADES_REACHED"
 *
 * 4. **Open Risk Limit**: openRisk < 4%
 *    - Reason: Account protection; prevent cascade losses from blowing out account
 *    - Threshold Rationale: 4% = conservative limit for demo; allows ~1 losing trade before stop
 *    - Source: docs/02-architecture/lld_v1.md § Portfolio Limits § Max Open Risk
 *    - Logged as: "MAX_OPEN_RISK_REACHED"
 *
 * @example
 * const decision = evaluateSignalLevelRisk({
 *   marketSnapshot: { atr20_1: 0.0050, spreadPrice: 0.0002, ... },
 *   accountSnapshot: { openTrades: 2, openRisk: 0.02, ... },
 *   ...
 * });
 *
 * if (!decision.approved) {
 *   console.log("Trade vetoed:", decision.reasonCodes);
 *   // Output example: ["SPREAD_TOO_WIDE"]
 * }
 *
 * @see evaluateAccountLevelRisk for portfolio-level checks
 * @see RISK_LIMITS for all threshold definitions
 */
export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
  const reasons: string[] = [];
  const atr = input.marketSnapshot.atr20_1;
  const spread = input.marketSnapshot.spreadPrice ?? 0;

  // ATR Validity Check: must be positive
  if (atr <= 0) {
    reasons.push("INVALID_ATR");
  }

  // Spread Guard: spread/atr ratio must be ≤ RISK_LIMITS.maxSpreadAtrRatio (20% of ATR)
  // Threshold: If ATR = 50 pips, allowed spread = 10 pips max
  if (spread > 0 && atr > 0 && spread / atr > RISK_LIMITS.maxSpreadAtrRatio) {
    reasons.push("SPREAD_TOO_WIDE");
  }

  // Open Trades Limit: must be < RISK_LIMITS.maxOpenTrades (6 positions)
  // Rationale: Correlation risk limit; max 6 concurrent positions
  if ((input.accountSnapshot.openTrades ?? 0) >= RISK_LIMITS.maxOpenTrades) {
    reasons.push("MAX_OPEN_TRADES_REACHED");
  }

  // Open Risk Limit: must be < RISK_LIMITS.maxOpenRiskPct (4% of account)
  // Rationale: Account blowout protection; conservative demo threshold
  if ((input.accountSnapshot.openRisk ?? 0) >= RISK_LIMITS.maxOpenRiskPct) {
    reasons.push("MAX_OPEN_RISK_REACHED");
  }

  return { approved: reasons.length === 0, reasonCodes: reasons };
}

/**
 * Evaluate account-level portfolio risk controls.
 *
 * Checks cumulative risk across the portfolio and enforces account-level constraints.
 * Used by the portfolio endpoint to batch-evaluate multiple proposed trades.
 *
 * @param input Risk check request with proposed trade and account snapshots
 * @returns Risk decision with approval status and veto reason codes
 *
 * Constraints checked (any violation → VETOED):
 *
 * 1. **Open Risk Budget**: (openRisk + proposedRisk) ≤ maxOpenRiskPct
 *    - Reason: Cumulative risk limit prevents account blowout
 *    - Default: 4% (from RISK_LIMITS.maxOpenRiskPct)
 *    - Logged as: "OPEN_RISK_LIMIT"
 *
 * 2. **Open Trades Budget**: (openTrades + 1) ≤ maxOpenTrades
 *    - Reason: Position count limit prevents correlation concentration
 *    - Default: 6 positions (from RISK_LIMITS.maxOpenTrades)
 *    - Logged as: "OPEN_TRADES_LIMIT"
 *
 * 3. **Daily Loss Limit**: dailyLossPct ≥ dailyLossLimitPct
 *    - Reason: Stop trading for the day if loss cap reached
 *    - Default: 3% (from RISK_LIMITS.dailyLossLimitPct)
 *    - Logged as: "DAILY_LOSS_LIMIT"
 *
 * 4. **Weekly Loss Limit**: weeklyLossPct ≥ weeklyLossLimitPct
 *    - Reason: Stop trading for the week if loss cap reached
 *    - Default: 6% (from RISK_LIMITS.weeklyLossLimitPct)
 *    - Logged as: "WEEKLY_LOSS_LIMIT"
 *
 * @example
 * const decision = evaluateAccountLevelRisk({
 *   proposedRiskPct: 0.02,
 *   proposedOpenTrades: 1,
 *   accountSnapshot: { openRisk: 0.01, openTrades: 2, dailyLossPct: 0.005, ... },
 *   maxOpenRisk: 0.04,
 *   maxOpenTrades: 6,
 * });
 *
 * if (!decision.approved) {
 *   console.log("Portfolio decision vetoed:", decision.vetoReasonCodes);
 *   // Output example: ["OPEN_RISK_LIMIT"]
 * }
 *
 * @see evaluateSignalLevelRisk for signal-level checks
 * @see RISK_LIMITS for default threshold definitions
 */
export function evaluateAccountLevelRisk(input: RiskCheckRequest): RiskCheckResponse {
  const reasons: string[] = [];
  const maxOpenRisk = input.maxOpenRisk ?? RISK_LIMITS.maxOpenRiskPct;
  const maxOpenTrades = input.maxOpenTrades ?? RISK_LIMITS.maxOpenTrades;
  const dailyLossLimitPct = input.dailyLossLimitPct ?? RISK_LIMITS.dailyLossLimitPct;
  const weeklyLossLimitPct = input.weeklyLossLimitPct ?? RISK_LIMITS.weeklyLossLimitPct;

  // Open Risk Budget: cumulative open risk must not exceed limit
  if ((input.accountSnapshot.openRisk ?? 0) + input.proposedRiskPct > maxOpenRisk) {
    reasons.push("OPEN_RISK_LIMIT");
  }

  // Open Trades Budget: proposed trade would exceed limit
  if ((input.accountSnapshot.openTrades ?? 0) + input.proposedOpenTrades > maxOpenTrades) {
    reasons.push("OPEN_TRADES_LIMIT");
  }

  // Daily Loss Limit: if daily loss exceeds limit, no more trades today
  if ((input.accountSnapshot.dailyLossPct ?? 0) >= dailyLossLimitPct) {
    reasons.push("DAILY_LOSS_LIMIT");
  }

  // Weekly Loss Limit: if weekly loss exceeds limit, no more trades this week
  if ((input.accountSnapshot.weeklyLossPct ?? 0) >= weeklyLossLimitPct) {
    reasons.push("WEEKLY_LOSS_LIMIT");
  }

  return {
    approved: reasons.length === 0,
    vetoReasonCodes: reasons,
    adjustedSize: reasons.length > 0 ? 0 : 1,
    evaluatedAtUtc: new Date().toISOString(),
  };
}
