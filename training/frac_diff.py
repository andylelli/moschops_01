"""
Fractionally differentiated features (de Prado, AFML Ch. 5).

The Fixed-Width Window Fracdiff (FFD) method preserves maximum memory
while achieving stationarity — unlike integer differencing which destroys
all long-range dependence.

No dependencies beyond numpy and pandas (statsmodels is lazy-imported only
for find_min_ffd).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ffd_weights(d: float, size: int, thres: float = 1e-5) -> np.ndarray:
    """
    Compute the FFD weight vector for differencing order d.

    Weights are truncated once |w_k| < thres to keep the window finite.
    The returned array has the oldest weight first (convolution order).
    """
    w: list[float] = [1.0]
    for k in range(1, size):
        w_k = -w[-1] * (d - k + 1) / k
        if abs(w_k) < thres:
            break
        w.append(w_k)
    return np.array(w[::-1])  # oldest first


def frac_diff_ffd(
    series: pd.Series,
    d: float,
    thres: float = 1e-5,
) -> pd.Series:
    """
    Apply Fixed-Width Window Fractional Differencing to a price series.

    For each bar i, computes the dot product of the weight vector with the
    preceding window of closes.  Bars in the warmup period are NaN.

    Parameters
    ----------
    series : pd.Series — raw (non-stationary) price series
    d      : float    — differencing order in (0, 1].  d=1 → integer diff.
    thres  : float    — weight truncation threshold (smaller = wider window)

    Returns
    -------
    pd.Series of fractionally differenced values, same index as series.
    """
    if not 0 < d <= 1:
        raise ValueError(f"d must be in (0, 1], got {d}")

    w = _ffd_weights(d, len(series), thres)
    width = len(w)
    arr = series.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)

    for i in range(width - 1, len(arr)):
        window = arr[i - width + 1 : i + 1]
        if np.any(~np.isfinite(window)):
            continue
        out[i] = float(np.dot(w, window))

    name = f"{series.name}_ffd_{d:.2f}" if series.name else f"ffd_{d:.2f}"
    return pd.Series(out, index=series.index, name=name)


def find_min_ffd(
    series: pd.Series,
    d_candidates: list[float] | None = None,
    significance: float = 0.05,
    thres: float = 1e-5,
) -> float:
    """
    Find the minimum d such that the FFD series passes an ADF stationarity test.

    Requires statsmodels.  Returns 1.0 as a safe fallback if statsmodels is
    not installed or no d achieves stationarity.

    Parameters
    ----------
    series       : pd.Series — raw price series
    d_candidates : list of d values to try in ascending order.
                   Defaults to [0.1, 0.2, ..., 1.0].
    significance : float — ADF p-value threshold for stationarity
    thres        : float — weight truncation threshold for FFD

    Returns
    -------
    float — minimum d achieving stationarity, or 1.0 if none found.
    """
    try:
        from statsmodels.tsa.stattools import adfuller  # noqa: PLC0415
    except ImportError:
        return 1.0

    if d_candidates is None:
        d_candidates = [round(x, 2) for x in np.arange(0.1, 1.01, 0.1).tolist()]

    for d in d_candidates:
        diff_series = frac_diff_ffd(series, d, thres).dropna()
        if len(diff_series) < 20:
            continue
        try:
            p_value = adfuller(diff_series, maxlag=1, regression="c", autolag=None)[1]
        except Exception:
            continue
        if p_value < significance:
            return float(d)

    return 1.0


def add_frac_diff_features(
    df: pd.DataFrame,
    cols: list[str] | None = None,
    d: float | None = None,
    thres: float = 1e-5,
) -> pd.DataFrame:
    """
    Add fractionally differenced versions of price columns to df.

    If d is None, find_min_ffd is called for each column to find the
    minimum d that achieves stationarity.

    Parameters
    ----------
    df   : pd.DataFrame with price columns
    cols : list of column names to transform (default: ["close"])
    d    : float | None — fixed d; None → auto-detect per column
    thres: float — weight truncation threshold

    Returns
    -------
    Copy of df with additional {col}_ffd_{d} columns.
    """
    df = df.copy()
    if cols is None:
        cols = ["close"]

    for col in cols:
        if col not in df.columns:
            continue
        d_use = d if d is not None else find_min_ffd(df[col], thres=thres)
        ffd = frac_diff_ffd(df[col], d=d_use, thres=thres)
        df[ffd.name] = ffd

    return df
