/**
 * P1 technical indicator functions for OHLCV time series.
 *
 * Each function accepts arrays ordered oldest → newest and returns
 * the SINGLE most-recent value (for inference-time use where only
 * the current bar's feature value is needed).
 *
 * These implementations mirror training/features.py exactly so that
 * training and inference produce identical feature values.
 *
 * All functions return NaN when there are insufficient bars for warmup.
 */

// ── EMA helpers ──────────────────────────────────────────────────────────────

/**
 * Wilder's smoothing EMA (alpha = 1/period).
 * Equivalent to pandas ewm(alpha=1/period, adjust=False).
 */
function wilderEma(values: number[], period: number): number[] {
  const alpha = 1.0 / period;
  const out: number[] = new Array(values.length).fill(NaN);
  let prev = NaN;
  for (let i = 0; i < values.length; i++) {
    if (!isFinite(values[i])) continue;
    if (!isFinite(prev)) {
      prev = values[i];
    } else {
      prev = alpha * values[i] + (1 - alpha) * prev;
    }
    out[i] = prev;
  }
  return out;
}

/**
 * Span-based EMA (alpha = 2 / (span + 1)).
 * Equivalent to pandas ewm(span=span, adjust=False).
 */
function spanEma(values: number[], span: number): number[] {
  const alpha = 2.0 / (span + 1);
  const out: number[] = new Array(values.length).fill(NaN);
  let prev = NaN;
  for (let i = 0; i < values.length; i++) {
    if (!isFinite(values[i])) continue;
    if (!isFinite(prev)) {
      prev = values[i];
    } else {
      prev = alpha * values[i] + (1 - alpha) * prev;
    }
    out[i] = prev;
  }
  return out;
}

function rollingMean(values: number[], period: number): number[] {
  const out: number[] = new Array(values.length).fill(NaN);
  let sum = 0;
  let count = 0;
  for (let i = 0; i < values.length; i++) {
    if (isFinite(values[i])) { sum += values[i]; count++; }
    if (i >= period) {
      const old = values[i - period];
      if (isFinite(old)) { sum -= old; count--; }
    }
    if (count === period) out[i] = sum / period;
  }
  return out;
}

function rollingStd(values: number[], period: number): number[] {
  const means = rollingMean(values, period);
  const out: number[] = new Array(values.length).fill(NaN);
  for (let i = period - 1; i < values.length; i++) {
    const slice = values.slice(i - period + 1, i + 1);
    if (slice.some((v) => !isFinite(v))) continue;
    const mu = means[i];
    const variance = slice.reduce((acc, v) => acc + (v - mu) ** 2, 0) / (period - 1);
    out[i] = Math.sqrt(variance);
  }
  return out;
}

function diff(values: number[], lag = 1): number[] {
  return values.map((v, i) => (i < lag ? NaN : v - values[i - lag]));
}

function absDiff(values: number[], lag = 1): number[] {
  return diff(values, lag).map(Math.abs);
}

function rollingMax(values: number[], period: number): number[] {
  const out: number[] = new Array(values.length).fill(NaN);
  for (let i = period - 1; i < values.length; i++) {
    let max = -Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      if (isFinite(values[j]) && values[j] > max) max = values[j];
    }
    out[i] = max === -Infinity ? NaN : max;
  }
  return out;
}

function rollingMin(values: number[], period: number): number[] {
  const out: number[] = new Array(values.length).fill(NaN);
  for (let i = period - 1; i < values.length; i++) {
    let min = Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      if (isFinite(values[j]) && values[j] < min) min = values[j];
    }
    out[i] = min === Infinity ? NaN : min;
  }
  return out;
}

// ── True Range ────────────────────────────────────────────────────────────────

function trueRange(highs: number[], lows: number[], closes: number[]): number[] {
  const n = closes.length;
  const tr: number[] = new Array(n).fill(NaN);
  tr[0] = highs[0] - lows[0];
  for (let i = 1; i < n; i++) {
    tr[i] = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1]),
    );
  }
  return tr;
}

// ── Public indicator functions ────────────────────────────────────────────────

/**
 * Wilder RSI.  Requires ≥ (period + 1) bars.  Returns the last value.
 */
export function rsi(closes: number[], period = 14): number {
  if (closes.length < period + 1) return NaN;
  const gains = diff(closes).map((v) => Math.max(0, isFinite(v) ? v : 0));
  const losses = diff(closes).map((v) => Math.max(0, isFinite(v) ? -v : 0));
  const avgGain = wilderEma(gains, period);
  const avgLoss = wilderEma(losses, period);
  const last = closes.length - 1;
  const ag = avgGain[last];
  const al = avgLoss[last];
  if (!isFinite(ag) || !isFinite(al)) return NaN;
  if (al === 0) return 100;
  return 100 - 100 / (1 + ag / al);
}

/**
 * MACD line (EMA(fast) − EMA(slow)).  Returns the last value.
 */
export function macdLine(closes: number[], fast = 12, slow = 26): number {
  if (closes.length < slow) return NaN;
  const emaFast = spanEma(closes, fast);
  const emaSlow = spanEma(closes, slow);
  const last = closes.length - 1;
  return isFinite(emaFast[last]) && isFinite(emaSlow[last])
    ? emaFast[last] - emaSlow[last]
    : NaN;
}

/**
 * MACD signal line (EMA(signal) of the MACD line).  Returns the last value.
 */
export function macdSignalLine(closes: number[], fast = 12, slow = 26, signal = 9): number {
  if (closes.length < slow + signal) return NaN;
  const emaFast = spanEma(closes, fast);
  const emaSlow = spanEma(closes, slow);
  const line = emaFast.map((v, i) => (isFinite(v) && isFinite(emaSlow[i]) ? v - emaSlow[i] : NaN));
  const signalLine = spanEma(line, signal);
  return signalLine[signalLine.length - 1];
}

/**
 * MACD histogram (line − signal).  Returns the last value.
 */
export function macdHistogram(closes: number[], fast = 12, slow = 26, signal = 9): number {
  const line = macdLine(closes, fast, slow);
  const sig = macdSignalLine(closes, fast, slow, signal);
  return isFinite(line) && isFinite(sig) ? line - sig : NaN;
}

/**
 * Bollinger Band width ((upper − lower) / middle).  Returns the last value.
 */
export function bollingerWidth(closes: number[], period = 20, numStd = 2.0): number {
  if (closes.length < period) return NaN;
  const ma = rollingMean(closes, period);
  const sd = rollingStd(closes, period);
  const last = closes.length - 1;
  const m = ma[last];
  const s = sd[last];
  if (!isFinite(m) || !isFinite(s) || m === 0) return NaN;
  return (2 * numStd * s) / m;
}

/**
 * Bollinger %B ((close − lower) / (upper − lower)).  Returns the last value.
 */
export function bollingerPctB(closes: number[], period = 20, numStd = 2.0): number {
  if (closes.length < period) return NaN;
  const ma = rollingMean(closes, period);
  const sd = rollingStd(closes, period);
  const last = closes.length - 1;
  const m = ma[last];
  const s = sd[last];
  if (!isFinite(m) || !isFinite(s) || s === 0) return NaN;
  const upper = m + numStd * s;
  const lower = m - numStd * s;
  const bandwidth = upper - lower;
  if (bandwidth === 0) return NaN;
  return (closes[last] - lower) / bandwidth;
}

/**
 * ADX + DI values.  Returns { adx, plusDi, minusDi } for the last bar.
 */
export function adx(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 14,
): { adx: number; plusDi: number; minusDi: number } {
  const NaN3 = { adx: NaN, plusDi: NaN, minusDi: NaN };
  const n = closes.length;
  if (n < period + 1) return NaN3;

  const tr = trueRange(highs, lows, closes);
  const upMove = diff(highs);
  const downMove = diff(lows).map((v) => -v);

  const plusDm = upMove.map((u, i) =>
    isFinite(u) && isFinite(downMove[i]) && u > downMove[i] && u > 0 ? u : 0,
  );
  const minusDm = downMove.map((d, i) =>
    isFinite(d) && isFinite(upMove[i]) && d > upMove[i] && d > 0 ? d : 0,
  );

  const atrArr = wilderEma(tr, period);
  const plusDiArr = wilderEma(plusDm, period).map((v, i) =>
    isFinite(v) && isFinite(atrArr[i]) && atrArr[i] > 0 ? (100 * v) / atrArr[i] : NaN,
  );
  const minusDiArr = wilderEma(minusDm, period).map((v, i) =>
    isFinite(v) && isFinite(atrArr[i]) && atrArr[i] > 0 ? (100 * v) / atrArr[i] : NaN,
  );
  const dxArr = plusDiArr.map((p, i) => {
    const m = minusDiArr[i];
    if (!isFinite(p) || !isFinite(m) || p + m === 0) return NaN;
    return (100 * Math.abs(p - m)) / (p + m);
  });
  const adxArr = wilderEma(dxArr, period);

  const last = n - 1;
  return { adx: adxArr[last], plusDi: plusDiArr[last], minusDi: minusDiArr[last] };
}

/**
 * Squeeze on flag: 1 when Bollinger Bands are inside Keltner Channels.
 */
export function squeezeOn(
  highs: number[],
  lows: number[],
  closes: number[],
  bbPeriod = 20,
  kcPeriod = 20,
  bbMult = 2.0,
  kcMult = 1.5,
): number {
  const n = closes.length;
  if (n < Math.max(bbPeriod, kcPeriod)) return NaN;
  const basis = rollingMean(closes, bbPeriod);
  const bbStd = rollingStd(closes, bbPeriod);
  const tr = trueRange(highs, lows, closes);
  const atr = rollingMean(tr, kcPeriod);
  const last = n - 1;
  const b = basis[last];
  const s = bbStd[last];
  const a = atr[last];
  if (!isFinite(b) || !isFinite(s) || !isFinite(a)) return NaN;
  const bbU = b + bbMult * s;
  const bbL = b - bbMult * s;
  const kcU = b + kcMult * a;
  const kcL = b - kcMult * a;
  return bbU < kcU && bbL > kcL ? 1 : 0;
}

/**
 * Squeeze momentum: (close − (highest + lowest) / 2) / ATR.
 */
export function squeezeMomentum(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 20,
): number {
  const n = closes.length;
  if (n < period) return NaN;
  const highest = rollingMax(highs, period);
  const lowest = rollingMin(lows, period);
  const tr = trueRange(highs, lows, closes);
  const atr = rollingMean(tr, period);
  const last = n - 1;
  const h = highest[last];
  const l = lowest[last];
  const a = atr[last];
  if (!isFinite(h) || !isFinite(l) || !isFinite(a) || a === 0) return NaN;
  return (closes[last] - (h + l) / 2) / a;
}

/**
 * Supertrend direction: +1 = uptrend, -1 = downtrend.
 * Mirrors the Python add_supertrend() implementation exactly.
 */
export function supertrendDir(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 7,
  multiplier = 3.0,
): number {
  const n = closes.length;
  if (n < period + 1) return NaN;

  const tr: number[] = new Array(n).fill(0);
  tr[0] = highs[0] - lows[0];
  for (let i = 1; i < n; i++) {
    tr[i] = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1]),
    );
  }

  // Wilder ATR
  const alpha = 1.0 / period;
  const atr: number[] = new Array(n).fill(0);
  atr[0] = tr[0];
  for (let i = 1; i < n; i++) {
    atr[i] = alpha * tr[i] + (1 - alpha) * atr[i - 1];
  }

  const hl2 = closes.map((_, i) => (highs[i] + lows[i]) / 2);
  const upper: number[] = hl2.map((h, i) => h + multiplier * atr[i]);
  const lower: number[] = hl2.map((h, i) => h - multiplier * atr[i]);

  let direction = 1;
  let supertrend = lower[0];

  for (let i = 1; i < n; i++) {
    // Ratchet bands
    if (closes[i - 1] > supertrend) {
      lower[i] = Math.max(lower[i], lower[i - 1]);
    } else {
      upper[i] = Math.min(upper[i], upper[i - 1]);
    }
    if (closes[i] > upper[i - 1]) {
      direction = 1;
    } else if (closes[i] < lower[i - 1]) {
      direction = -1;
    }
    supertrend = direction === 1 ? lower[i] : upper[i];
  }
  return direction;
}

/**
 * KAMA slope (5-bar slope of KAMA).
 */
export function kamaSlope(
  closes: number[],
  fastPeriod = 2,
  slowPeriod = 30,
  window = 10,
): number {
  const n = closes.length;
  if (n < window + 5) return NaN;
  const fastSc = 2.0 / (fastPeriod + 1);
  const slowSc = 2.0 / (slowPeriod + 1);

  const kama: number[] = new Array(n).fill(NaN);
  kama[window - 1] = closes[window - 1];

  for (let i = window; i < n; i++) {
    const direction = Math.abs(closes[i] - closes[i - window]);
    let path = 0;
    for (let j = i - window + 1; j <= i; j++) {
      path += Math.abs(closes[j] - closes[j - 1]);
    }
    const er = path > 0 ? direction / path : 0;
    const sc = (er * (fastSc - slowSc) + slowSc) ** 2;
    kama[i] = kama[i - 1] + sc * (closes[i] - kama[i - 1]);
  }

  const last = n - 1;
  if (!isFinite(kama[last]) || !isFinite(kama[last - 5])) return NaN;
  return (kama[last] - kama[last - 5]) / 5;
}

/**
 * Linear regression slope over the last [period] closes.
 */
export function lrSlope(closes: number[], period = 20): number {
  if (closes.length < period) return NaN;
  const slice = closes.slice(-period);
  if (slice.some((v) => !isFinite(v))) return NaN;
  const x = Array.from({ length: period }, (_, i) => i);
  const xMean = (period - 1) / 2;
  const yMean = slice.reduce((a, b) => a + b, 0) / period;
  let num = 0;
  let den = 0;
  for (let i = 0; i < period; i++) {
    num += (x[i] - xMean) * (slice[i] - yMean);
    den += (x[i] - xMean) ** 2;
  }
  return den > 0 ? num / den : NaN;
}

/**
 * R-squared of the linear regression over the last [period] closes.
 */
export function lrR2(closes: number[], period = 20): number {
  if (closes.length < period) return NaN;
  const slice = closes.slice(-period);
  if (slice.some((v) => !isFinite(v))) return NaN;
  const slope = lrSlope(closes, period);
  if (!isFinite(slope)) return NaN;
  const xMean = (period - 1) / 2;
  const yMean = slice.reduce((a, b) => a + b, 0) / period;
  let ssRes = 0;
  let ssTot = 0;
  for (let i = 0; i < period; i++) {
    const yHat = slope * (i - xMean) + yMean;
    ssRes += (slice[i] - yHat) ** 2;
    ssTot += (slice[i] - yMean) ** 2;
  }
  return ssTot > 1e-12 ? 1 - ssRes / ssTot : 0;
}

/**
 * Volume ratio: last volume / 20-bar rolling mean volume.
 */
export function volumeRatio(volumes: number[], period = 20): number {
  if (volumes.length < period) return NaN;
  const ma = rollingMean(volumes, period);
  const last = volumes.length - 1;
  const m = ma[last];
  return isFinite(m) && m > 0 ? volumes[last] / m : NaN;
}

/**
 * Volume momentum: 1-bar change in volume / 20-bar mean volume.
 */
export function volumeMomentum(volumes: number[], period = 20): number {
  if (volumes.length < period + 1) return NaN;
  const ma = rollingMean(volumes, period);
  const last = volumes.length - 1;
  const m = ma[last];
  if (!isFinite(m) || m === 0) return NaN;
  return (volumes[last] - volumes[last - 1]) / m;
}

/**
 * Day of week from a UTC date string or Date.  0 = Monday … 4 = Friday.
 * Returns the JS getDay() value remapped to ISO weekday (Mon=0).
 */
export function dayOfWeek(barCloseTimeUtc: string | Date): number {
  const d = typeof barCloseTimeUtc === "string" ? new Date(barCloseTimeUtc) : barCloseTimeUtc;
  return (d.getUTCDay() + 6) % 7; // Sun=0 in JS → Mon=0 in ISO
}

/** 1 if the bar closed on a Monday, 0 otherwise. */
export function isMonday(barCloseTimeUtc: string | Date): number {
  return dayOfWeek(barCloseTimeUtc) === 0 ? 1 : 0;
}

/** 1 if the bar closed on a Friday, 0 otherwise. */
export function isFriday(barCloseTimeUtc: string | Date): number {
  return dayOfWeek(barCloseTimeUtc) === 4 ? 1 : 0;
}

/**
 * Hurst exponent via variance scaling (H = slope(log(var), log(lag)) / 2).
 * H > 0.5 → trending, H < 0.5 → mean-reverting.
 */
export function hurstExponent(
  closes: number[],
  minLag = 2,
  maxLag = 15,
  window = 60,
): number {
  if (closes.length < window + maxLag) return NaN;
  const series = closes.slice(-window);
  const lags: number[] = [];
  const logVars: number[] = [];

  for (let lag = minLag; lag <= maxLag; lag++) {
    const diffs: number[] = [];
    for (let i = lag; i < series.length; i++) {
      diffs.push(series[i] - series[i - lag]);
    }
    if (diffs.length === 0) continue;
    const mean = diffs.reduce((a, b) => a + b, 0) / diffs.length;
    const variance = diffs.reduce((a, v) => a + (v - mean) ** 2, 0) / diffs.length;
    if (variance <= 0) continue;
    lags.push(Math.log(lag));
    logVars.push(Math.log(variance));
  }

  if (lags.length < 3) return NaN;
  // Simple OLS slope
  const n = lags.length;
  const xMean = lags.reduce((a, b) => a + b, 0) / n;
  const yMean = logVars.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    num += (lags[i] - xMean) * (logVars[i] - yMean);
    den += (lags[i] - xMean) ** 2;
  }
  return den > 0 ? num / den / 2 : NaN;
}

/**
 * CUSUM filter statistic (accumulated excess directional drift).
 * Higher value = more accumulated directional movement.
 */
export function cusumStat(closes: number[], lookback = 20): number {
  const n = closes.length;
  if (n < lookback + 1) return NaN;

  const logRets: number[] = new Array(n).fill(0);
  for (let i = 1; i < n; i++) {
    logRets[i] = closes[i] > 0 && closes[i - 1] > 0 ? Math.log(closes[i] / closes[i - 1]) : 0;
  }

  // Rolling std for threshold
  const stds = rollingStd(logRets, lookback);

  let sPos = 0;
  let sNeg = 0;
  for (let i = 1; i < n; i++) {
    const thresh = isFinite(stds[i]) ? stds[i] * 0.5 : 0;
    sPos = Math.max(0, sPos + logRets[i] - thresh);
    sNeg = Math.max(0, sNeg - logRets[i] - thresh);
  }
  return sPos + sNeg;
}

/**
 * Kaufman Efficiency Ratio: direction / path over [period] bars.
 * ER ≈ 1 → trending, ER ≈ 0 → choppy.
 */
export function efficiencyRatio(closes: number[], period = 10): number {
  const n = closes.length;
  if (n < period + 1) return NaN;
  const direction = Math.abs(closes[n - 1] - closes[n - 1 - period]);
  let path = 0;
  for (let i = n - period; i < n; i++) {
    path += Math.abs(closes[i] - closes[i - 1]);
  }
  return path > 0 ? direction / path : NaN;
}

// ── Convenience: compute all P1 features for one bar ─────────────────────────

export interface P1Features {
  rsi: number;
  macd_line: number;
  macd_signal: number;
  macd_hist: number;
  bb_width: number;
  bb_pct_b: number;
  adx: number;
  adx_plus_di: number;
  adx_minus_di: number;
  squeeze_on: number;
  squeeze_momentum: number;
  supertrend_dir: number;
  kama_slope: number;
  lr_slope: number;
  lr_r2: number;
  volume_ratio: number;
  volume_momentum: number;
  day_of_week: number;
  is_monday: number;
  is_friday: number;
  hurst: number;
  cusum: number;
  efficiency_ratio: number;
}

export interface OHLCVBar {
  barCloseTimeUtc: string | Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

/**
 * Compute all 23 P1 features from an array of OHLCV bars.
 * Bars must be ordered oldest → newest.
 * Requires ≥ 60 bars for reliable Hurst; ≥ 50 for all other features.
 */
export function computeP1Features(bars: OHLCVBar[]): P1Features {
  const closes = bars.map((b) => b.close);
  const highs = bars.map((b) => b.high);
  const lows = bars.map((b) => b.low);
  const volumes = bars.map((b) => b.volume ?? 0);
  const lastBar = bars[bars.length - 1];

  const adxResult = adx(highs, lows, closes);

  return {
    rsi: rsi(closes),
    macd_line: macdLine(closes),
    macd_signal: macdSignalLine(closes),
    macd_hist: macdHistogram(closes),
    bb_width: bollingerWidth(closes),
    bb_pct_b: bollingerPctB(closes),
    adx: adxResult.adx,
    adx_plus_di: adxResult.plusDi,
    adx_minus_di: adxResult.minusDi,
    squeeze_on: squeezeOn(highs, lows, closes),
    squeeze_momentum: squeezeMomentum(highs, lows, closes),
    supertrend_dir: supertrendDir(highs, lows, closes),
    kama_slope: kamaSlope(closes),
    lr_slope: lrSlope(closes),
    lr_r2: lrR2(closes),
    volume_ratio: volumeRatio(volumes),
    volume_momentum: volumeMomentum(volumes),
    day_of_week: dayOfWeek(lastBar.barCloseTimeUtc),
    is_monday: isMonday(lastBar.barCloseTimeUtc),
    is_friday: isFriday(lastBar.barCloseTimeUtc),
    hurst: hurstExponent(closes),
    cusum: cusumStat(closes),
    efficiency_ratio: efficiencyRatio(closes),
  };
}

/** Ordered list of P1 feature names (matches training/features.py P1_FEATURE_NAMES). */
export const P1_FEATURE_NAMES: (keyof P1Features)[] = [
  "rsi",
  "macd_line",
  "macd_signal",
  "macd_hist",
  "bb_width",
  "bb_pct_b",
  "adx",
  "adx_plus_di",
  "adx_minus_di",
  "squeeze_on",
  "squeeze_momentum",
  "supertrend_dir",
  "kama_slope",
  "lr_slope",
  "lr_r2",
  "volume_ratio",
  "volume_momentum",
  "day_of_week",
  "is_monday",
  "is_friday",
  "hurst",
  "cusum",
  "efficiency_ratio",
];

/** Convert a P1Features object to a flat number array in canonical feature order. */
export function p1FeaturesToArray(features: P1Features): number[] {
  return P1_FEATURE_NAMES.map((k) => features[k]);
}
