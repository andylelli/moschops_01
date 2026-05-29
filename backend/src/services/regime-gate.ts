/**
 * Regime Gate — Volatility-based AI threshold adjustment
 *
 * Detects elevated or extreme volatility regimes by comparing a short-term
 * rolling volatility window against a longer baseline. When the regime ratio
 * exceeds thresholds, the AI confidence gate is tightened (threshold bumped up)
 * to suppress entries during structurally uncertain conditions.
 *
 * This is the backend equivalent of a simplified BOCPD change-point detector.
 * Threshold bumps make the model more conservative without disabling it entirely.
 *
 * Source: docs/02-architecture/lld_v1.md § Layered Defence § Regime Gate
 */

export type RegimeLabel = "NORMAL" | "ELEVATED" | "EXTREME";

export interface RegimeStatus {
  regimeLabel: RegimeLabel;
  regimeRatio: number;
  thresholdBump: number;
  recentVol: number;
  baselineVol: number;
  sampleCount: number;
}

// Rolling window sizes
const RECENT_WINDOW = 20;
const BASELINE_WINDOW = 100;

// Regime ratio thresholds → threshold bumps
const BUMP_EXTREME = { ratio: 3.0, bump: 0.06 } as const;
const BUMP_ELEVATED = { ratio: 2.0, bump: 0.04 } as const;
const BUMP_MILD = { ratio: 1.5, bump: 0.02 } as const;

/**
 * Rolling volatility window tracker.
 * Maintains last BASELINE_WINDOW volatility readings in a circular buffer.
 * Thread-safe for single-threaded Node.js event loop.
 */
class RegimeGate {
  private readonly buf: Float64Array;
  private head = 0;
  private count = 0;

  constructor() {
    this.buf = new Float64Array(BASELINE_WINDOW);
  }

  /**
   * Record the volatility for the latest bar and update the buffer.
   * Call once per bar processed.
   */
  recordBar(volatility: number): void {
    if (!Number.isFinite(volatility) || volatility <= 0) {
      return; // Skip invalid readings — do not corrupt the buffer
    }
    this.buf[this.head] = volatility;
    this.head = (this.head + 1) % BASELINE_WINDOW;
    if (this.count < BASELINE_WINDOW) {
      this.count++;
    }
  }

  /**
   * Returns the current regime status and threshold bump.
   * If fewer than RECENT_WINDOW samples have been recorded, returns NORMAL
   * with no bump (insufficient data → conservative: allow through).
   */
  getStatus(): RegimeStatus {
    if (this.count < RECENT_WINDOW) {
      return {
        regimeLabel: "NORMAL",
        regimeRatio: 1.0,
        thresholdBump: 0,
        recentVol: 0,
        baselineVol: 0,
        sampleCount: this.count,
      };
    }

    const recentVol = this._mean(RECENT_WINDOW);
    const baselineVol = this._mean(this.count);

    if (baselineVol <= 0) {
      return {
        regimeLabel: "NORMAL",
        regimeRatio: 1.0,
        thresholdBump: 0,
        recentVol,
        baselineVol,
        sampleCount: this.count,
      };
    }

    const regimeRatio = recentVol / baselineVol;

    let regimeLabel: RegimeLabel = "NORMAL";
    let thresholdBump = 0;

    if (regimeRatio >= BUMP_EXTREME.ratio) {
      regimeLabel = "EXTREME";
      thresholdBump = BUMP_EXTREME.bump;
    } else if (regimeRatio >= BUMP_ELEVATED.ratio) {
      regimeLabel = "ELEVATED";
      thresholdBump = BUMP_ELEVATED.bump;
    } else if (regimeRatio >= BUMP_MILD.ratio) {
      regimeLabel = "ELEVATED";
      thresholdBump = BUMP_MILD.bump;
    }

    return {
      regimeLabel,
      regimeRatio,
      thresholdBump,
      recentVol,
      baselineVol,
      sampleCount: this.count,
    };
  }

  /** Mean of the last `n` entries (n ≤ this.count ≤ BASELINE_WINDOW). */
  private _mean(n: number): number {
    const len = Math.min(n, this.count);
    let sum = 0;
    for (let i = 0; i < len; i++) {
      // Walk backwards from head in the circular buffer
      const idx = (this.head - 1 - i + BASELINE_WINDOW) % BASELINE_WINDOW;
      sum += this.buf[idx];
    }
    return sum / len;
  }

  /** Reset state (e.g., on strategy restart). */
  reset(): void {
    this.buf.fill(0);
    this.head = 0;
    this.count = 0;
  }
}

/**
 * Per-strategy regime gate instances, keyed by `${strategyId}:${symbol}:${timeframe}`.
 * Each strategy+symbol combination tracks its own volatility baseline.
 */
const instances = new Map<string, RegimeGate>();

function getGate(strategyId: string, symbol: string, timeframe: string): RegimeGate {
  const key = `${strategyId}:${symbol}:${timeframe}`;
  let gate = instances.get(key);
  if (!gate) {
    gate = new RegimeGate();
    instances.set(key, gate);
  }
  return gate;
}

/**
 * Record a volatility reading for the given strategy/symbol/timeframe.
 * Call once per bar in the signal route.
 */
export function recordBarVolatility(
  strategyId: string,
  symbol: string,
  timeframe: string,
  volatility: number
): void {
  getGate(strategyId, symbol, timeframe).recordBar(volatility);
}

/**
 * Get the current regime status including the AI threshold bump.
 * Call after recordBarVolatility on the same bar.
 */
export function getRegimeStatus(
  strategyId: string,
  symbol: string,
  timeframe: string
): RegimeStatus {
  return getGate(strategyId, symbol, timeframe).getStatus();
}

/**
 * Reset all regime gate state (e.g., for testing).
 */
export function resetAllRegimeGates(): void {
  instances.clear();
}
