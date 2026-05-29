"""
Correlation-aware portfolio position sizing.

When holding multiple correlated instruments simultaneously, the naive sum of
individual Kelly / vol-scaled lots overstates diversification and understates
portfolio risk.  This module adjusts position sizes to account for cross-asset
correlations so that the target portfolio volatility is maintained.

Also provides:
- Kelly fraction and half-Kelly for a single strategy
- Diversification ratio (Choueifat et al.) as a portfolio quality metric

Usage:
    from portfolio_sizing import (
        correlation_adjusted_lots,
        kelly_fraction,
        half_kelly,
        diversification_ratio,
    )
"""
from __future__ import annotations

import numpy as np


def correlation_adjusted_lots(
    base_lots: np.ndarray | list[float],
    corr_matrix: np.ndarray,
    individual_vols: np.ndarray | list[float] | None = None,
    target_portfolio_vol: float = 0.01,
    min_lot: float = 0.01,
    max_lot: float = 5.0,
) -> np.ndarray:
    """
    Adjust position lots so the portfolio hits the target volatility.

    The portfolio variance is:
        σ_p² = w' Σ w
    where w_i = lots_i × vol_i and Σ = correlation matrix.

    We scale the lot vector uniformly so that σ_p = target_portfolio_vol.

    Parameters
    ----------
    base_lots           : array-like shape (n,) — initial lot sizes per instrument
    corr_matrix         : np.ndarray shape (n, n) — correlation matrix of instruments
    individual_vols     : array-like shape (n,) | None — per-instrument volatility.
                          If None, assumes unit vol for all (lots ≡ vol-weights).
    target_portfolio_vol: float — desired portfolio 1-period volatility
    min_lot             : float — minimum lot size (floor per instrument)
    max_lot             : float — maximum lot size (cap per instrument)

    Returns
    -------
    np.ndarray of float shape (n,) — adjusted lot sizes
    """
    base_lots = np.asarray(base_lots, dtype=float)
    corr_matrix = np.asarray(corr_matrix, dtype=float)
    n = len(base_lots)

    if corr_matrix.shape != (n, n):
        raise ValueError(f"corr_matrix must be ({n},{n}); got {corr_matrix.shape}")

    if individual_vols is None:
        individual_vols = np.ones(n)
    individual_vols = np.asarray(individual_vols, dtype=float)

    # vol-scaled weights
    w = base_lots * individual_vols
    # Portfolio variance
    port_var = float(w @ corr_matrix @ w)
    port_std = float(np.sqrt(max(port_var, 1e-20)))

    if port_std < 1e-12:
        return np.clip(base_lots, min_lot, max_lot)

    # Scale factor to hit target
    scale = target_portfolio_vol / port_std
    adjusted = base_lots * scale
    return np.clip(adjusted, min_lot, max_lot)


def kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    """
    Full Kelly fraction for a binary win/loss strategy.

    Kelly formula:  f* = (p * b - q) / b
    where b = avg_win / avg_loss,  q = 1 - p.

    Parameters
    ----------
    win_rate : float — probability of winning (0 < win_rate < 1)
    avg_win  : float — average fractional gain on winning trades (> 0)
    avg_loss : float — average fractional loss on losing trades (> 0, absolute value)

    Returns
    -------
    float Kelly fraction in [0, 1].  Returns 0 if the edge is non-positive.
    """
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    b = avg_win / avg_loss
    f = (win_rate * b - (1.0 - win_rate)) / b
    return float(np.clip(f, 0.0, 1.0))


def half_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    """
    Half-Kelly fraction (50% of full Kelly) — a practical conservative default.

    Full Kelly is theoretically optimal for long-run growth but maximises the
    risk of catastrophic drawdowns; half-Kelly sacrifices ~25% of growth rate
    in exchange for roughly halving volatility.

    Returns
    -------
    float in [0, 0.5]
    """
    return kelly_fraction(win_rate, avg_win, avg_loss) / 2.0


def diversification_ratio(
    weights: np.ndarray | list[float],
    corr_matrix: np.ndarray,
    individual_vols: np.ndarray | list[float] | None = None,
) -> float:
    """
    Choueifat diversification ratio: DR = Σ(w_i σ_i) / σ_p.

    DR = 1 means no diversification benefit (all perfectly correlated).
    DR > 1 means the portfolio benefits from low correlations.

    Parameters
    ----------
    weights         : array-like shape (n,) — portfolio weights (should sum to 1)
    corr_matrix     : np.ndarray shape (n, n)
    individual_vols : array-like shape (n,) | None — per-instrument volatility

    Returns
    -------
    float DR ≥ 1 (or 1.0 if the portfolio has zero vol)
    """
    weights = np.asarray(weights, dtype=float)
    corr_matrix = np.asarray(corr_matrix, dtype=float)
    n = len(weights)

    if individual_vols is None:
        individual_vols = np.ones(n)
    individual_vols = np.asarray(individual_vols, dtype=float)

    # Covariance matrix
    diag = np.diag(individual_vols)
    cov = diag @ corr_matrix @ diag

    weighted_avg_vol = float(np.dot(weights, individual_vols))
    port_var = float(weights @ cov @ weights)
    port_std = float(np.sqrt(max(port_var, 1e-20)))

    if port_std < 1e-12 or weighted_avg_vol < 1e-12:
        return 1.0

    return float(weighted_avg_vol / port_std)


def equal_risk_contribution_weights(
    corr_matrix: np.ndarray,
    individual_vols: np.ndarray | list[float] | None = None,
    n_iter: int = 300,
) -> np.ndarray:
    """
    Compute Equal Risk Contribution (ERC) portfolio weights iteratively.

    ERC weights each asset so that its contribution to total portfolio risk is
    equal.  This is a popular risk-parity approach.

    Parameters
    ----------
    corr_matrix     : np.ndarray shape (n, n)
    individual_vols : array-like shape (n,) | None
    n_iter          : int — number of gradient descent iterations

    Returns
    -------
    np.ndarray shape (n,) — normalised weights (sum to 1)
    """
    n = corr_matrix.shape[0]
    if individual_vols is None:
        individual_vols = np.ones(n)
    individual_vols = np.asarray(individual_vols, dtype=float)

    diag = np.diag(individual_vols)
    cov = diag @ corr_matrix @ diag

    w = np.ones(n, dtype=float) / n
    lr = 0.01

    for _ in range(n_iter):
        port_var = float(w @ cov @ w)
        port_std = float(np.sqrt(max(port_var, 1e-20)))
        mrc = cov @ w / port_std          # marginal risk contribution
        rc = w * mrc                       # risk contribution
        target_rc = port_std / n
        grad = rc - target_rc
        w = w - lr * grad
        w = np.maximum(w, 1e-6)
        w /= w.sum()

    return w
