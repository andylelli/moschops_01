/**
 * Risk Control Thresholds and Limits
 * Source: docs/02-architecture/lld_v1.md § Risk Engine Controls
 * 
 * This module centralizes all risk-related configuration to ensure consistency
 * across all decision points (signal, portfolio, account levels).
 */
import { recordFileLog } from "../services/file-log";

export const RISK_LIMITS = {
  // Portfolio-level limits
  maxOpenRiskPct: 0.04,        // 4% max open risk across all positions
  maxOpenTrades: 6,             // Max 6 concurrent positions (correlation limit)
  
  // Signal-level limits
  maxRiskPerTradePct: 0.005,    // 0.5% max risk per individual trade
  maxSpreadAtrRatio: 0.2,       // Spread must be ≤ 20% of ATR (spread guard)
  
  // AI scoring thresholds for position sizing
  aiScoreThresholds: {
    full: 0.65,   // score ≥ 0.65 → FULL sizing
    half: 0.55,   // score ∈ [0.55, 0.65) → HALF sizing
    skip: 0.0,    // score < 0.55 → SKIP (no trade)
  },
  
  // Daily/weekly loss limits
  dailyLossLimitPct: 0.03,      // 3% daily loss cap
  weeklyLossLimitPct: 0.06,     // 6% weekly loss cap

  // Circuit breaker — consecutive loss trip threshold
  maxConsecutiveLosses: 5,      // Trip after 5 consecutive losing trades

  // Regime gate — AI threshold bumps on elevated volatility
  regimeGate: {
    bumpMild: 0.02,             // vol_regime > 1.5 → +0.02 to AI threshold
    bumpElevated: 0.04,         // vol_regime > 2.0 → +0.04 to AI threshold
    bumpExtreme: 0.06,          // vol_regime > 3.0 → +0.06 to AI threshold
  },
} as const;

/**
 * Validate risk limits consistency at app startup.
 * Ensures no configuration drift or invalid threshold pairs.
 * 
 * @throws Error if thresholds are invalid or inconsistent
 * 
 * @example
 * // Called during app initialization
 * validateRiskLimits();
 * console.log("✓ Risk limits validated and ready");
 */
export function validateRiskLimits(): void {
  const { aiScoreThresholds } = RISK_LIMITS;
  
  // Check score threshold ordering
  if (aiScoreThresholds.half >= aiScoreThresholds.full) {
    throw new Error(
      `Invalid AI score thresholds: half (${aiScoreThresholds.half}) must be < full (${aiScoreThresholds.full})`
    );
  }
  
  // Check score ranges
  if (aiScoreThresholds.skip < 0 || aiScoreThresholds.full > 1) {
    throw new Error(
      `AI score thresholds must be in range [0, 1]; got skip=${aiScoreThresholds.skip}, full=${aiScoreThresholds.full}`
    );
  }
  
  // Check reasonable limits
  if (RISK_LIMITS.maxOpenRiskPct <= 0 || RISK_LIMITS.maxOpenRiskPct > 1) {
    throw new Error(
      `maxOpenRiskPct must be in (0, 1]; got ${RISK_LIMITS.maxOpenRiskPct}`
    );
  }
  
  if (RISK_LIMITS.maxOpenTrades <= 0 || RISK_LIMITS.maxOpenTrades > 100) {
    throw new Error(
      `maxOpenTrades must be in (0, 100]; got ${RISK_LIMITS.maxOpenTrades}`
    );
  }
  
  recordFileLog({
    category: "startup",
    level: "info",
    event: "risk_limits_validated",
    message: "Risk limits validated successfully",
  });
  console.log("✓ Risk limits validated successfully");
}
