"""
Market regime detection features.

Implements:
- HMM-based regime labeling  (lazy import: hmmlearn)
- GARCH(1,1) / EGARCH conditional volatility  (lazy import: arch)

Both are standalone; neither depends on existing training scripts.
If the optional libraries are absent the functions degrade gracefully
(zeros for HMM labels, rolling-std for GARCH vol).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── HMM ──────────────────────────────────────────────────────────────────────

def hmm_regime_labels(
    returns: pd.Series | np.ndarray,
    n_states: int = 2,
    n_iter: int = 100,
    covariance_type: str = "full",
    random_state: int = 42,
) -> np.ndarray:
    """
    Fit a Gaussian HMM to return observations and return per-bar regime labels.

    Labels are re-mapped so that 0 = lowest-mean-return state (bearish/choppy)
    and n_states-1 = highest-mean-return state (bullish/trending).  This keeps
    label semantics consistent across runs regardless of HMM initialisation order.

    Requires hmmlearn.  Returns an array of zeros if not installed.

    Parameters
    ----------
    returns         : log or simple returns (1-D)
    n_states        : number of hidden states
    n_iter          : EM iterations for fitting
    covariance_type : "full" | "diag" | "spherical"
    random_state    : reproducibility seed

    Returns
    -------
    np.ndarray of int, shape (n,).
    """
    arr = np.asarray(returns, dtype=float).reshape(-1, 1)

    try:
        from hmmlearn.hmm import GaussianHMM  # noqa: PLC0415
    except ImportError:
        return np.zeros(len(arr), dtype=int)

    model = GaussianHMM(
        n_components=n_states,
        covariance_type=covariance_type,
        n_iter=n_iter,
        random_state=random_state,
    )
    model.fit(arr)
    raw_labels = model.predict(arr)

    # Re-map: label 0 → lowest mean return regime
    means = model.means_.flatten()
    order = np.argsort(means)
    remap = {int(old): int(new) for new, old in enumerate(order)}
    return np.array([remap[int(lbl)] for lbl in raw_labels], dtype=int)


def hmm_regime_feature(
    df: pd.DataFrame,
    n_states: int = 2,
    price_col: str = "close",
) -> pd.DataFrame:
    """
    Compute log returns, fit HMM, and add an 'hmm_regime' integer column to df.

    Returns a copy of df.
    """
    df = df.copy()
    log_ret = np.log(df[price_col] / df[price_col].shift(1)).fillna(0.0)
    df["hmm_regime"] = hmm_regime_labels(log_ret, n_states=n_states)
    return df


# ── GARCH / EGARCH ────────────────────────────────────────────────────────────

def garch_conditional_vol(
    returns: pd.Series | np.ndarray,
    p: int = 1,
    q: int = 1,
    dist: str = "normal",
    vol_model: str = "GARCH",
) -> np.ndarray:
    """
    Fit a GARCH(p,q) or EGARCH(p,q) model and return per-bar conditional volatility.

    Requires the arch package.  Falls back to a 21-bar rolling standard deviation
    if arch is not installed.

    Parameters
    ----------
    returns   : log or simple returns (1-D)
    p         : ARCH lag order
    q         : GARCH lag order
    dist      : error distribution — "normal" | "t" | "skewt"
    vol_model : "GARCH" | "EGARCH"

    Returns
    -------
    np.ndarray of conditional volatility values in the same units as returns.
    """
    arr = np.asarray(returns, dtype=float)

    try:
        from arch import arch_model  # noqa: PLC0415
    except ImportError:
        # Fallback: rolling std
        return pd.Series(arr).rolling(21, min_periods=1).std().to_numpy(dtype=float)

    # arch expects returns expressed as percent
    scaled = arr * 100.0
    am = arch_model(scaled, vol=vol_model, p=p, q=q, dist=dist, rescale=False)
    res = am.fit(disp="off", show_warning=False)
    # conditional_volatility is in % units; convert back to return-scale
    return (res.conditional_volatility / 100.0).to_numpy(dtype=float)


def garch_vol_feature(
    df: pd.DataFrame,
    price_col: str = "close",
    p: int = 1,
    q: int = 1,
    vol_model: str = "GARCH",
) -> pd.DataFrame:
    """
    Compute log returns, fit GARCH/EGARCH, and add a 'garch_vol' column to df.

    Returns a copy of df.
    """
    df = df.copy()
    log_ret = np.log(df[price_col] / df[price_col].shift(1)).fillna(0.0)
    df["garch_vol"] = garch_conditional_vol(log_ret, p=p, q=q, vol_model=vol_model)
    return df
