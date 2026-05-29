"""
Position sizing utilities.

Implements:
- Volatility-scaled position sizing (ATR-based fixed-fractional risk)
- Equity-curve risk scaling (half-size when equity is below its MA)

No external dependencies beyond numpy and pandas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def vol_scaled_lot(
    atr: float,
    account_equity: float,
    risk_pct: float = 0.01,
    pip_value: float = 10.0,
    pip_size: float = 0.0001,
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Compute the ATR-based fixed-fractional lot size.

    Risk formula:
        risk_amount = account_equity × risk_pct
        atr_pips    = atr / pip_size
        lot         = risk_amount / (atr_pips × pip_value)

    Parameters
    ----------
    atr            : float — current ATR in price units (e.g. 0.00085 for EURUSD)
    account_equity : float — current account equity in account currency
    risk_pct       : float — fraction of equity to risk per trade (default = 1 %)
    pip_value      : float — monetary value of one pip per standard lot (default = $10)
    pip_size       : float — price units per pip (default = 0.0001 for 4-digit pairs)
    min_lot        : float — minimum position size in lots
    max_lot        : float — maximum position size in lots

    Returns
    -------
    float — position size in lots, clamped to [min_lot, max_lot].
    """
    if atr <= 0 or account_equity <= 0 or pip_size <= 0 or pip_value <= 0:
        return float(min_lot)

    risk_amount = account_equity * risk_pct
    atr_pips = atr / pip_size
    if atr_pips <= 0:
        return float(min_lot)

    lot = risk_amount / (atr_pips * pip_value)
    return float(np.clip(lot, min_lot, max_lot))


def equity_curve_scalar(
    equity_curve: pd.Series | np.ndarray,
    ma_period: int = 20,
    below_ma_scale: float = 0.5,
    above_ma_scale: float = 1.0,
) -> np.ndarray:
    """
    Compute a per-bar position size scalar based on equity-curve health.

    When the equity curve is below its moving average (draw-down mode) the
    scalar is below_ma_scale (default 0.5 = half size).  When at or above the
    MA the scalar is above_ma_scale (default 1.0 = full size).

    Parameters
    ----------
    equity_curve   : sequence of account balance / NAV values
    ma_period      : int   — rolling MA lookback period
    below_ma_scale : float — size multiplier when equity < MA
    above_ma_scale : float — size multiplier when equity ≥ MA

    Returns
    -------
    np.ndarray of float scalars, shape (n,).
    """
    arr = np.asarray(equity_curve, dtype=float)
    ma = (
        pd.Series(arr)
        .rolling(ma_period, min_periods=1)
        .mean()
        .to_numpy(dtype=float)
    )
    return np.where(arr >= ma, above_ma_scale, below_ma_scale).astype(float)


def apply_sizing(
    base_lot: float,
    eq_scalar: float,
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Multiply base_lot by the equity-curve scalar and clamp to valid range.

    Parameters
    ----------
    base_lot  : float — lot size from vol_scaled_lot()
    eq_scalar : float — scalar from equity_curve_scalar() for the current bar
    min_lot   : float — minimum lot size
    max_lot   : float — maximum lot size

    Returns
    -------
    float — final lot size.
    """
    return float(np.clip(base_lot * eq_scalar, min_lot, max_lot))
