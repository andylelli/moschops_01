"""
Multi-timeframe confirmation utilities.

Resamples OHLCV bar data to a higher timeframe (HTF) and checks for
directional alignment between the lower (LTF) and higher (HTF) timeframes.
A signal is only confirmed when both frames agree.

Usage:
    from multiframe import resample_ohlcv, add_htf_trend, mtf_confirmed_signal

    weekly = resample_ohlcv(daily_df, rule="W")
    daily_df = add_htf_trend(daily_df, weekly, ma_period=10)
    confirmed = mtf_confirmed_signal(daily_signal, daily_df["htf_trend"])
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str = "W") -> pd.DataFrame:
    """
    Resample OHLCV bars to a higher timeframe using standard OHLCV aggregation.

    Parameters
    ----------
    df   : pd.DataFrame with columns {open, high, low, close} (volume optional)
           and a DatetimeIndex.
    rule : str — pandas offset alias, e.g. "W" (weekly), "ME" (month-end),
           "2W" (bi-weekly).

    Returns
    -------
    Resampled OHLCV DataFrame with rows containing at least one valid close.
    """
    agg: dict[str, str] = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    }
    if "volume" in df.columns:
        agg["volume"] = "sum"

    return df.resample(rule).agg(agg).dropna(subset=["close"])


def add_htf_trend(
    ltf_df: pd.DataFrame,
    htf_df: pd.DataFrame,
    ma_period: int = 20,
    col: str = "close",
    feature_name: str = "htf_trend",
) -> pd.DataFrame:
    """
    Compute a +1/−1 trend signal on the HTF DataFrame and merge it into
    the LTF DataFrame via forward-fill.

    The HTF trend is:
      +1 when HTF close > HTF rolling MA
      −1 when HTF close ≤ HTF rolling MA

    Each LTF bar inherits the last available HTF signal (ffill).

    Parameters
    ----------
    ltf_df       : low-timeframe DataFrame (DatetimeIndex)
    htf_df       : high-timeframe DataFrame (DatetimeIndex)
    ma_period    : int — MA period applied to the HTF series
    col          : str — column to derive the trend from (default "close")
    feature_name : str — name of the new column in ltf_df

    Returns
    -------
    Copy of ltf_df with feature_name column added.
    """
    htf_ma = htf_df[col].rolling(ma_period, min_periods=1).mean()
    htf_trend = np.sign(htf_df[col] - htf_ma).rename(feature_name)

    ltf_df = ltf_df.copy()
    ltf_df = ltf_df.join(htf_trend, how="left")
    ltf_df[feature_name] = ltf_df[feature_name].ffill().fillna(0.0)
    return ltf_df


def mtf_confirmed_signal(
    ltf_signal: pd.Series,
    htf_trend: pd.Series,
) -> pd.Series:
    """
    Return a confirmed signal that is 1 only when both:
    - the LTF signal is positive (probability > 0 or label == 1), AND
    - the HTF trend is positive (+1)

    All other bars are 0.

    Parameters
    ----------
    ltf_signal : pd.Series — LTF signal or probability (0/1 or continuous)
    htf_trend  : pd.Series — HTF trend values (−1 / 0 / +1)

    Returns
    -------
    pd.Series of int {0, 1} named "mtf_confirmed", aligned to ltf_signal.index.
    """
    aligned_htf = htf_trend.reindex(ltf_signal.index).ffill().fillna(0.0)
    confirmed = (ltf_signal > 0) & (aligned_htf > 0)
    return confirmed.astype(int).rename("mtf_confirmed")
