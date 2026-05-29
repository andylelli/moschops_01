"""
Regime-conditional P&L attribution and structural break testing.

Implements:
- regime_pnl_attribution : break down return stats by regime label
- chow_test              : single-break-point Chow F-test
- rolling_structural_breaks : rolling minimum p-value from Chow tests

scipy.stats is available transitively via scikit-learn.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def regime_pnl_attribution(
    returns: pd.Series | np.ndarray,
    regimes: pd.Series | np.ndarray,
    annualisation: float = 252.0,
) -> dict[int, dict]:
    """
    Compute return statistics (mean, std, Sharpe, cumulative) for each regime.

    Parameters
    ----------
    returns       : per-bar strategy returns (e.g. mark-to-market P&L per bar)
    regimes       : integer regime labels aligned bar-for-bar with returns
    annualisation : float — factor for annualised Sharpe (252 = daily bars)

    Returns
    -------
    dict mapping regime_label (int) → {mean, std, sharpe, n_bars, cum_return}
    """
    r = np.asarray(returns, dtype=float)
    g = np.asarray(regimes, dtype=int)
    result: dict[int, dict] = {}

    for regime in np.unique(g):
        mask = g == regime
        subset = r[mask]
        n = int(mask.sum())
        mean = float(np.mean(subset)) if n > 0 else 0.0
        std = float(np.std(subset, ddof=1)) if n > 1 else 0.0
        sharpe = float(mean / std * np.sqrt(annualisation)) if std > 0 else 0.0
        cum_ret = float(np.sum(subset))
        result[int(regime)] = {
            "mean": round(mean, 8),
            "std": round(std, 8),
            "sharpe": round(sharpe, 4),
            "n_bars": n,
            "cum_return": round(cum_ret, 6),
        }
    return result


def chow_test(
    series: pd.Series | np.ndarray,
    break_idx: int,
) -> dict:
    """
    Chow structural break test for a univariate series at a given index.

    Tests whether the conditional mean differs significantly before and after
    break_idx using an F-statistic under the assumption of equal variance.

    Parameters
    ----------
    series    : 1-D numeric series
    break_idx : int — 0-based position of the proposed break point

    Returns
    -------
    dict with keys: f_statistic, p_value, break_idx, significant (p < 0.05)
    """
    from scipy.stats import f as f_dist  # noqa: PLC0415

    arr = np.asarray(series, dtype=float)
    n = len(arr)

    if break_idx < 2 or break_idx > n - 2:
        return {
            "f_statistic": np.nan,
            "p_value": np.nan,
            "break_idx": break_idx,
            "significant": False,
        }

    seg1 = arr[:break_idx]
    seg2 = arr[break_idx:]

    # Unrestricted RSS: separate means per segment
    rss_u = float(
        np.sum((seg1 - seg1.mean()) ** 2) + np.sum((seg2 - seg2.mean()) ** 2)
    )
    # Restricted RSS: single mean for full series
    rss_r = float(np.sum((arr - arr.mean()) ** 2))

    k = 1  # number of restricted parameters (mean)
    dof_u = n - 2 * k
    if dof_u <= 0 or rss_u <= 1e-12:
        return {
            "f_statistic": np.nan,
            "p_value": np.nan,
            "break_idx": break_idx,
            "significant": False,
        }

    f_stat = float(((rss_r - rss_u) / k) / (rss_u / dof_u))
    p_val = float(1.0 - f_dist.cdf(f_stat, dfn=k, dfd=dof_u))

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_val, 6),
        "break_idx": break_idx,
        "significant": p_val < 0.05,
    }


def rolling_structural_breaks(
    series: pd.Series | np.ndarray,
    window: int = 60,
    min_segment: int = 10,
) -> pd.Series:
    """
    Slide a window over the series and compute the minimum Chow p-value
    among all valid break points within that window.

    A low p-value indicates strong evidence of a structural break somewhere
    inside the current window.

    Parameters
    ----------
    series      : 1-D numeric series
    window      : int — rolling window length
    min_segment : int — minimum bars required on each side of a break point

    Returns
    -------
    pd.Series of float (min Chow p-value per bar, NaN for warmup).
    """
    arr = np.asarray(series, dtype=float)
    idx = series.index if isinstance(series, pd.Series) else np.arange(len(arr))
    n = len(arr)
    out = np.full(n, np.nan)

    for i in range(window - 1, n):
        sub = arr[i - window + 1 : i + 1]
        p_vals: list[float] = []
        for bp in range(min_segment, window - min_segment):
            res = chow_test(sub, bp)
            pv = res.get("p_value")
            if pv is not None and np.isfinite(pv):
                p_vals.append(pv)
        out[i] = float(min(p_vals)) if p_vals else np.nan

    return pd.Series(out, index=idx, name="chow_min_p")
