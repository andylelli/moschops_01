"""
Ichimoku Cloud technical indicator features.

Computes all five Ichimoku components plus derived boolean features for
use as ML input features or signal filters.

Components:
- Tenkan-sen  (conversion line) : midpoint of highest-high + lowest-low over 9 bars
- Kijun-sen   (base line)       : midpoint of highest-high + lowest-low over 26 bars
- Senkou Span A (leading span A): (tenkan + kijun) / 2, projected 26 bars forward
- Senkou Span B (leading span B): midpoint of highest-high + lowest-low over 52 bars,
                                  projected 26 bars forward
- Chikou Span  (lagging span)   : close shifted 26 bars back

Derived boolean features (aligned to current bar, using the cloud from 26 bars ago):
- cloud_bullish    : Senkou A > Senkou B (green cloud)
- price_above_cloud: close > max(Senkou A, Senkou B) from the current cloud
- tk_cross_bull    : tenkan crossed above kijun (1 bar ago → current)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_ichimoku(
    df: pd.DataFrame,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
) -> pd.DataFrame:
    """
    Add Ichimoku Cloud components to df.

    Columns added:
    - tenkan_sen       : conversion line
    - kijun_sen        : base line
    - senkou_a         : leading span A (shifted forward by displacement)
    - senkou_b         : leading span B (shifted forward by displacement)
    - chikou_span      : lagging span (close shifted back by displacement)
    - cloud_bullish    : 1 when the current bar's cloud is green (Span A > Span B)
    - price_above_cloud: 1 when close is above the current cloud
    - tk_cross_bull    : 1 when tenkan crossed above kijun on the current bar

    Parameters
    ----------
    df               : pd.DataFrame with columns {high, low, close}
    tenkan_period    : int — conversion line period (default 9)
    kijun_period     : int — base line period       (default 26)
    senkou_b_period  : int — leading span B period  (default 52)
    displacement     : int — cloud projection / chikou shift  (default 26)

    Returns
    -------
    Copy of df with new Ichimoku columns.
    """
    df = df.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    def midpoint(h: pd.Series, l: pd.Series, period: int) -> pd.Series:
        return (h.rolling(period).max() + l.rolling(period).min()) / 2.0

    tenkan = midpoint(high, low, tenkan_period)
    kijun = midpoint(high, low, kijun_period)
    senkou_a_raw = ((tenkan + kijun) / 2.0).shift(displacement)
    senkou_b_raw = midpoint(high, low, senkou_b_period).shift(displacement)
    chikou = close.shift(-displacement)  # projected backwards = close shifted back

    df["tenkan_sen"] = tenkan
    df["kijun_sen"] = kijun
    df["senkou_a"] = senkou_a_raw
    df["senkou_b"] = senkou_b_raw
    df["chikou_span"] = chikou

    # Derived features aligned to current bar:
    # The "cloud" at the current bar was projected 'displacement' bars ago,
    # so we use the raw (un-shifted) Span A and B aligned to current.
    senkou_a_current = (tenkan + kijun) / 2.0
    senkou_b_current = midpoint(high, low, senkou_b_period)

    df["cloud_bullish"] = (senkou_a_current > senkou_b_current).astype(float)

    cloud_top = np.maximum(senkou_a_current, senkou_b_current)
    df["price_above_cloud"] = (close > cloud_top).astype(float)

    # TK cross: tenkan crossed above kijun (was below, now above)
    tk_cross = (
        (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
    ).astype(float)
    df["tk_cross_bull"] = tk_cross

    return df
