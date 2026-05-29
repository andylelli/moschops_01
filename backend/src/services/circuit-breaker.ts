/**
 * Circuit Breaker — Account-level trade suppression
 *
 * Trips and suppresses new trade entries when cumulative loss metrics exceed
 * configured thresholds. Operates on data from the accountSnapshot (computed
 * by the EA and included in each signal request).
 *
 * Three independent trip conditions:
 *   1. Daily loss limit — too much loss today
 *   2. Weekly loss limit — too much loss this week
 *   3. Consecutive losses — streak of losing bars (in-memory stateful)
 *
 * Condition 1 and 2 are stateless (based on accountSnapshot).
 * Condition 3 is stateful (requires recordOutcome() to be called per bar).
 *
 * Source: docs/02-architecture/lld_v1.md § Layered Defence § Circuit Breaker
 * Python reference: training/circuit_breaker.py
 */

export interface CircuitBreakerTrip {
  tripped: true;
  reasons: string[];
}

export interface CircuitBreakerClear {
  tripped: false;
}

export type CircuitBreakerStatus = CircuitBreakerTrip | CircuitBreakerClear;

export interface CircuitBreakerState {
  consecutiveLosses: number;
  maxConsecutiveLosses: number;
  dailyLossLimitPct: number;
  weeklyLossLimitPct: number;
}

/**
 * Stateful per-strategy circuit breaker.
 * Tracks consecutive losses in memory; resets when a winning bar is recorded.
 */
class CircuitBreakerInstance {
  private consecutiveLosses = 0;
  private readonly maxConsecutive: number;
  private readonly dailyLimitPct: number;
  private readonly weeklyLimitPct: number;

  constructor(maxConsecutive: number, dailyLimitPct: number, weeklyLimitPct: number) {
    this.maxConsecutive = maxConsecutive;
    this.dailyLimitPct = dailyLimitPct;
    this.weeklyLimitPct = weeklyLimitPct;
  }

  /**
   * Evaluate all circuit breaker conditions.
   *
   * @param dailyLossPct   Absolute cumulative daily loss fraction (e.g. 0.03 = 3%)
   * @param weeklyLossPct  Absolute cumulative weekly loss fraction (e.g. 0.06 = 6%)
   * @returns CircuitBreakerStatus — tripped=true blocks new trade entries
   */
  check(dailyLossPct: number, weeklyLossPct: number): CircuitBreakerStatus {
    const reasons: string[] = [];

    if (dailyLossPct >= this.dailyLimitPct) {
      reasons.push("CB_DAILY_LOSS_LIMIT");
    }

    if (weeklyLossPct >= this.weeklyLimitPct) {
      reasons.push("CB_WEEKLY_LOSS_LIMIT");
    }

    if (this.consecutiveLosses >= this.maxConsecutive) {
      reasons.push(`CB_CONSECUTIVE_LOSSES:${this.consecutiveLosses}`);
    }

    if (reasons.length > 0) {
      return { tripped: true, reasons };
    }

    return { tripped: false };
  }

  /**
   * Record the outcome of the most recent trade bar.
   * Call with won=true when the bar resulted in a winning/neutral trade,
   * won=false for a losing trade.
   *
   * @param won Whether the trade (or signal bar) was profitable
   */
  recordOutcome(won: boolean): void {
    if (won) {
      this.consecutiveLosses = 0;
    } else {
      this.consecutiveLosses++;
    }
  }

  getState(): CircuitBreakerState {
    return {
      consecutiveLosses: this.consecutiveLosses,
      maxConsecutiveLosses: this.maxConsecutive,
      dailyLossLimitPct: this.dailyLimitPct,
      weeklyLossLimitPct: this.weeklyLimitPct,
    };
  }

  reset(): void {
    this.consecutiveLosses = 0;
  }
}

/**
 * Per-strategy circuit breaker instances, keyed by strategyId.
 * Each strategy tracks its own consecutive-loss state independently.
 */
const instances = new Map<string, CircuitBreakerInstance>();

function getInstance(
  strategyId: string,
  maxConsecutiveLosses: number,
  dailyLossLimitPct: number,
  weeklyLossLimitPct: number
): CircuitBreakerInstance {
  let cb = instances.get(strategyId);
  if (!cb) {
    cb = new CircuitBreakerInstance(maxConsecutiveLosses, dailyLossLimitPct, weeklyLossLimitPct);
    instances.set(strategyId, cb);
  }
  return cb;
}

/**
 * Check the circuit breaker for the given strategy.
 * Creates a new instance with default limits on first call.
 *
 * @param strategyId        Strategy identifier
 * @param dailyLossPct      Absolute daily loss fraction from accountSnapshot
 * @param weeklyLossPct     Absolute weekly loss fraction from accountSnapshot
 * @param maxConsecutive    Max consecutive losses before trip (default: 5)
 * @param dailyLimitPct     Daily loss trip threshold (default: 0.03)
 * @param weeklyLimitPct    Weekly loss trip threshold (default: 0.06)
 */
export function checkCircuitBreaker(
  strategyId: string,
  dailyLossPct: number,
  weeklyLossPct: number,
  maxConsecutive = 5,
  dailyLimitPct = 0.03,
  weeklyLimitPct = 0.06
): CircuitBreakerStatus {
  return getInstance(strategyId, maxConsecutive, dailyLimitPct, weeklyLimitPct).check(
    dailyLossPct,
    weeklyLossPct
  );
}

/**
 * Record a trade outcome for the given strategy's consecutive-loss tracker.
 * Call after each closed trade: won=true for profit/breakeven, won=false for loss.
 */
export function recordTradeOutcome(strategyId: string, won: boolean): void {
  // Only update existing instances — don't create one just to record an outcome
  const cb = instances.get(strategyId);
  if (cb) {
    cb.recordOutcome(won);
  }
}

/**
 * Get current circuit breaker state for a strategy (for diagnostics/logging).
 */
export function getCircuitBreakerState(strategyId: string): CircuitBreakerState | null {
  return instances.get(strategyId)?.getState() ?? null;
}

/**
 * Reset all circuit breaker state (e.g., for testing or forced reset).
 */
export function resetAllCircuitBreakers(): void {
  instances.clear();
}
