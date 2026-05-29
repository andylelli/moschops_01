"""
External market feature fetching: DXY (US Dollar Index) and VIX.

Data source: Yahoo Finance via yfinance (lazy import).
Falls back gracefully to NaN-filled columns if yfinance is not installed
or the network fetch fails.

The input DataFrame must have a DatetimeIndex (UTC-aware or UTC-naive).

Usage:
    from external_features import add_dxy_feature, add_vix_feature
    df = add_dxy_feature(df)   # adds 'dxy_return', 'dxy_trend'
    df = add_vix_feature(df)   # adds 'vix_level', 'vix_percentile'
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_DXY_TICKER = "DX-Y.NYB"
_VIX_TICKER = "^VIX"


def _fetch_yahoo(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch daily OHLCV from Yahoo Finance. Returns empty DataFrame on any failure."""
    try:
        import yfinance as yf  # noqa: PLC0415
        raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if raw.empty:
            return pd.DataFrame()
        raw.index = pd.to_datetime(raw.index, utc=True)
        return raw
    except Exception:
        return pd.DataFrame()


def _close_col(df: pd.DataFrame) -> str:
    """Return the name of the close column in a yfinance DataFrame."""
    for name in ("Close", "close", "Adj Close"):
        if name in df.columns:
            return name
    return df.columns[3]  # fallback: 4th column


def add_dxy_feature(
    df: pd.DataFrame,
    lookback: int = 20,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Add US Dollar Index (DXY) features to df.

    Columns added:
    - dxy_return  : 1-day log return of DXY (positive = USD strengthening)
    - dxy_trend   : sign(DXY − DXY_MA), values +1 / 0 / −1

    Both columns are NaN for dates that do not align with a DXY trading day
    (weekends, US holidays) and for the MA warmup period.

    Parameters
    ----------
    df       : pd.DataFrame with DatetimeIndex
    lookback : int — MA period for dxy_trend
    start    : str | None — ISO date string for fetch start; defaults to df.index[0]
    end      : str | None — ISO date string for fetch end;   defaults to df.index[-1]

    Returns
    -------
    Copy of df with dxy_return and dxy_trend columns added.
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df["dxy_return"] = np.nan
        df["dxy_trend"] = np.nan
        return df

    s = start or str(df.index[0].date())
    e = end or str(df.index[-1].date())
    dxy = _fetch_yahoo(_DXY_TICKER, s, e)

    if dxy.empty:
        df["dxy_return"] = np.nan
        df["dxy_trend"] = np.nan
        return df

    col = _close_col(dxy)
    dxy_close = dxy[col].rename("dxy_close")
    dxy_ret = np.log(dxy_close / dxy_close.shift(1)).rename("dxy_return")
    dxy_ma = dxy_close.rolling(lookback, min_periods=1).mean()
    dxy_trend = np.sign(dxy_close - dxy_ma).rename("dxy_trend")

    df = df.join(dxy_ret, how="left")
    df = df.join(dxy_trend, how="left")
    return df


def add_vix_feature(
    df: pd.DataFrame,
    percentile_window: int = 252,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """
    Add CBOE Volatility Index (VIX) features to df.

    Columns added:
    - vix_level      : raw VIX close value (implied vol %)
    - vix_percentile : rolling percentile rank of VIX within percentile_window bars.
                       0.0 = historically low vol; 1.0 = historically high vol.

    Parameters
    ----------
    df                : pd.DataFrame with DatetimeIndex
    percentile_window : int — rolling window for percentile rank (default 252 = ~1 year)
    start             : str | None — ISO date string for fetch start
    end               : str | None — ISO date string for fetch end

    Returns
    -------
    Copy of df with vix_level and vix_percentile columns added.
    """
    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df["vix_level"] = np.nan
        df["vix_percentile"] = np.nan
        return df

    s = start or str(df.index[0].date())
    e = end or str(df.index[-1].date())
    vix = _fetch_yahoo(_VIX_TICKER, s, e)

    if vix.empty:
        df["vix_level"] = np.nan
        df["vix_percentile"] = np.nan
        return df

    col = _close_col(vix)
    vix_close = vix[col].rename("vix_level")
    vix_pct = (
        vix_close
        .rolling(percentile_window, min_periods=10)
        .apply(
            lambda x: float(np.sum(x <= x.iloc[-1])) / len(x),
            raw=False,
        )
        .rename("vix_percentile")
    )

    df = df.join(vix_close, how="left")
    df = df.join(vix_pct, how="left")
    return df
