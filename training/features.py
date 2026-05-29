"""
P1 feature engineering for OHLCV time series.

All public functions accept a pandas DataFrame with lowercase columns:
  open, high, low, close, volume
and a DatetimeIndex (or a 'date' column for calendar features).

Each function adds one or more feature columns to df and returns df.
Use build_feature_set(df) to apply the full P1 pipeline in one call.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── RSI ───────────────────────────────────────────────────────────────────────

def add_rsi(df: pd.DataFrame, period: int = 14, col: str = "close") -> pd.DataFrame:
    """Wilder RSI.  Output column: rsi (0–100)."""
    delta = df[col].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df["rsi"] = 100.0 - (100.0 / (1.0 + rs))
    return df


# ── MACD ─────────────────────────────────────────────────────────────────────

def add_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, col: str = "close"
) -> pd.DataFrame:
    """MACD line, signal line, histogram.  Output: macd_line, macd_signal, macd_hist."""
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd_line"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    return df


# ── Bollinger Bands ───────────────────────────────────────────────────────────

def add_bollinger(
    df: pd.DataFrame, period: int = 20, num_std: float = 2.0, col: str = "close"
) -> pd.DataFrame:
    """Bollinger Band width and %B.  Output: bb_width, bb_pct_b."""
    ma = df[col].rolling(period).mean()
    std = df[col].rolling(period).std()
    bb_upper = ma + num_std * std
    bb_lower = ma - num_std * std
    band_width = bb_upper - bb_lower
    df["bb_width"] = band_width / ma.replace(0.0, np.nan)
    df["bb_pct_b"] = (df[col] - bb_lower) / band_width.replace(0.0, np.nan)
    return df


# ── ADX ───────────────────────────────────────────────────────────────────────

def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Wilder ADX, +DI, -DI.  Output: adx, adx_plus_di, adx_minus_di."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move.values, 0.0),
        index=df.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move.values, 0.0),
        index=df.index,
    )

    alpha = 1.0 / period
    atr = tr.ewm(alpha=alpha, adjust=False).mean()
    plus_di_raw = plus_dm.ewm(alpha=alpha, adjust=False).mean()
    minus_di_raw = minus_dm.ewm(alpha=alpha, adjust=False).mean()

    plus_di = 100.0 * plus_di_raw / atr.replace(0.0, np.nan)
    minus_di = 100.0 * minus_di_raw / atr.replace(0.0, np.nan)

    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    df["adx"] = dx.ewm(alpha=alpha, adjust=False).mean()
    df["adx_plus_di"] = plus_di
    df["adx_minus_di"] = minus_di
    return df


# ── Squeeze Momentum ─────────────────────────────────────────────────────────

def add_squeeze_momentum(
    df: pd.DataFrame,
    bb_period: int = 20,
    bb_mult: float = 2.0,
    kc_period: int = 20,
    kc_mult: float = 1.5,
) -> pd.DataFrame:
    """
    LazyBear Squeeze Momentum.
    squeeze_on  = 1 when Bollinger Bands are inside Keltner Channels (compression).
    squeeze_momentum = normalised momentum delta (close relative to recent HL midpoint / ATR).
    """
    basis = df["close"].rolling(bb_period).mean()
    bb_std = df["close"].rolling(bb_period).std()
    bb_upper = basis + bb_mult * bb_std
    bb_lower = basis - bb_mult * bb_std

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(kc_period).mean()
    kc_upper = basis + kc_mult * atr
    kc_lower = basis - kc_mult * atr

    df["squeeze_on"] = ((bb_upper < kc_upper) & (bb_lower > kc_lower)).astype(float)

    highest = df["high"].rolling(bb_period).max()
    lowest = df["low"].rolling(bb_period).min()
    delta = df["close"] - (highest + lowest) / 2.0
    df["squeeze_momentum"] = delta / atr.replace(0.0, np.nan)
    return df


# ── Supertrend ────────────────────────────────────────────────────────────────

def add_supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Supertrend direction.  Output: supertrend_dir (+1 = uptrend, -1 = downtrend).
    Uses Wilder ATR internally.
    """
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    n = len(df)

    # True Range
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

    # Wilder ATR
    alpha = 1.0 / period
    atr = np.empty(n)
    atr[0] = tr[0]
    for i in range(1, n):
        atr[i] = alpha * tr[i] + (1.0 - alpha) * atr[i - 1]

    hl2 = (high + low) / 2.0
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    direction = np.ones(n)
    supertrend = lower.copy()

    for i in range(1, n):
        # Ratchet bands in trend direction to prevent band from reversing
        lower[i] = max(lower[i], lower[i - 1]) if close[i - 1] > supertrend[i - 1] else lower[i]
        upper[i] = min(upper[i], upper[i - 1]) if close[i - 1] <= supertrend[i - 1] else upper[i]

        if close[i] > upper[i - 1]:
            direction[i] = 1.0
        elif close[i] < lower[i - 1]:
            direction[i] = -1.0
        else:
            direction[i] = direction[i - 1]

        supertrend[i] = lower[i] if direction[i] == 1.0 else upper[i]

    df["supertrend_dir"] = direction
    return df


# ── KAMA ─────────────────────────────────────────────────────────────────────

def add_kama(
    df: pd.DataFrame,
    fast_period: int = 2,
    slow_period: int = 30,
    window: int = 10,
    col: str = "close",
) -> pd.DataFrame:
    """Kaufman Adaptive Moving Average slope.  Output: kama_slope."""
    fast_sc = 2.0 / (fast_period + 1)
    slow_sc = 2.0 / (slow_period + 1)
    price = df[col].values.astype(float)
    n = len(price)

    kama = np.full(n, np.nan)
    kama[window - 1] = price[window - 1]

    for i in range(window, n):
        direction = abs(price[i] - price[i - window])
        path = np.sum(np.abs(np.diff(price[i - window : i + 1])))
        er = direction / path if path > 0.0 else 0.0
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama[i] = kama[i - 1] + sc * (price[i] - kama[i - 1])

    kama_s = pd.Series(kama, index=df.index)
    df["kama_slope"] = kama_s.diff(5) / 5.0
    return df


# ── Linear Regression slope + R² ─────────────────────────────────────────────

def add_linear_regression_features(
    df: pd.DataFrame, period: int = 20, col: str = "close"
) -> pd.DataFrame:
    """Rolling linear regression slope and R².  Output: lr_slope, lr_r2."""
    price = df[col].values.astype(float)
    n = len(price)

    x = np.arange(period, dtype=float)
    x_mean = x.mean()
    x_c = x - x_mean
    x_ss = float(np.dot(x_c, x_c))

    slopes = np.full(n, np.nan)
    r2s = np.full(n, np.nan)

    for i in range(period - 1, n):
        y = price[i - period + 1 : i + 1]
        if np.any(np.isnan(y)):
            continue
        y_mean = y.mean()
        y_c = y - y_mean
        if x_ss < 1e-12:
            continue
        slope = float(np.dot(x_c, y_c)) / x_ss
        y_hat = slope * x_c + y_mean
        ss_res = float(np.dot(y - y_hat, y - y_hat))
        ss_tot = float(np.dot(y_c, y_c))
        r2 = (1.0 - ss_res / ss_tot) if ss_tot > 1e-12 else 0.0
        slopes[i] = slope
        r2s[i] = r2

    df["lr_slope"] = slopes
    df["lr_r2"] = r2s
    return df


# ── Volume Features ───────────────────────────────────────────────────────────

def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """Volume ratio (vs 20-bar MA) and 1-bar volume momentum.
    Output: volume_ratio, volume_momentum."""
    vol_ma = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / vol_ma.replace(0.0, np.nan)
    df["volume_momentum"] = df["volume"].diff(1) / vol_ma.replace(0.0, np.nan)
    return df


# ── Calendar Features ─────────────────────────────────────────────────────────

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Day-of-week and day-of-month features.
    Output: day_of_week (0=Mon–4=Fri), is_monday, is_friday."""
    if isinstance(df.index, pd.DatetimeIndex):
        dow = df.index.dayofweek
    elif "date" in df.columns:
        dow = pd.to_datetime(df["date"]).dt.dayofweek.values
    else:
        # Fallback for purely synthetic data without dates
        dow = np.arange(len(df)) % 5

    df["day_of_week"] = dow
    df["is_monday"] = (dow == 0).astype(float)
    df["is_friday"] = (dow == 4).astype(float)
    return df


# ── Hurst Exponent ────────────────────────────────────────────────────────────

def add_hurst_exponent(
    df: pd.DataFrame,
    min_lag: int = 2,
    max_lag: int = 15,
    window: int = 60,
    col: str = "close",
) -> pd.DataFrame:
    """
    Rolling Hurst exponent via variance scaling.
    H > 0.5 → trending, H < 0.5 → mean-reverting, H ≈ 0.5 → random walk.
    Output: hurst.
    """
    price = df[col].values.astype(float)
    n = len(price)
    lags = np.arange(min_lag, max_lag + 1, dtype=int)
    log_lags = np.log(lags.astype(float))

    def _hurst(ts: np.ndarray) -> float:
        variances = np.empty(len(lags))
        for k, lag in enumerate(lags):
            diffs = ts[lag:] - ts[:-lag]
            variances[k] = np.var(diffs) if len(diffs) > 0 else np.nan
        if np.any(~np.isfinite(variances)) or np.any(variances <= 0):
            return np.nan
        slope = np.polyfit(log_lags, np.log(variances), 1)[0]
        return float(slope / 2.0)

    hurst_vals = np.full(n, np.nan)
    for i in range(window, n):
        hurst_vals[i] = _hurst(price[i - window : i])

    df["hurst"] = hurst_vals
    return df


# ── CUSUM filter statistic ────────────────────────────────────────────────────

def add_cusum_feature(df: pd.DataFrame, col: str = "close", lookback: int = 20) -> pd.DataFrame:
    """
    CUSUM filter statistic (Lopez de Prado style).
    Accumulates excess drift in log-return space.  Resets are not applied so
    this behaves as a continuous drift-accumulation feature.
    Output: cusum (non-negative, higher = more accumulated directional drift).
    """
    log_ret = np.log(df[col] / df[col].shift(1)).fillna(0.0).values
    thresh = (
        pd.Series(log_ret).rolling(lookback).std().fillna(0.0).values * 0.5
    )

    s_pos = np.zeros(len(df))
    s_neg = np.zeros(len(df))
    for i in range(1, len(df)):
        s_pos[i] = max(0.0, s_pos[i - 1] + log_ret[i] - thresh[i])
        s_neg[i] = max(0.0, s_neg[i - 1] - log_ret[i] - thresh[i])

    df["cusum"] = s_pos + s_neg
    return df


# ── Efficiency Ratio ──────────────────────────────────────────────────────────

def add_efficiency_ratio(
    df: pd.DataFrame, period: int = 10, col: str = "close"
) -> pd.DataFrame:
    """
    Kaufman Efficiency Ratio: direction / volatility over [period] bars.
    ER ≈ 1 → strongly trending, ER ≈ 0 → choppy.
    Output: efficiency_ratio.
    """
    price = df[col]
    direction = price.diff(period).abs()
    path = price.diff(1).abs().rolling(period).sum()
    df["efficiency_ratio"] = direction / path.replace(0.0, np.nan)
    return df


# ── Master builder ────────────────────────────────────────────────────────────

def build_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the full P1 feature pipeline to a DataFrame with columns
    open, high, low, close, volume (and optional DatetimeIndex / 'date' column).

    Returns a copy of df with all P1 feature columns appended.
    NaN rows at the start of each rolling window are preserved;
    call df.dropna() after labelling to remove them.
    """
    df = df.copy()
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger(df)
    df = add_adx(df)
    df = add_squeeze_momentum(df)
    df = add_supertrend(df)
    df = add_kama(df)
    df = add_linear_regression_features(df)
    df = add_volume_features(df)
    df = add_calendar_features(df)
    df = add_hurst_exponent(df)
    df = add_cusum_feature(df)
    df = add_efficiency_ratio(df)
    return df


# ── Canonical feature list ────────────────────────────────────────────────────

P1_FEATURE_NAMES: list[str] = [
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
]
