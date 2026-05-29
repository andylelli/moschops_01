"""
Monte Carlo equity curve simulation.

Bootstraps trade-return sequences to create many possible equity curve paths
and computes distributional statistics (drawdown, Sharpe, ruin probability).

This is used to stress-test a strategy beyond the single realised equity curve:
even a profitable strategy can fail under alternative orderings of the same trades.

Usage:
    from mc_simulation import (
        bootstrap_equity_curves, mc_drawdown_stats, mc_sharpe_distribution
    )

    paths = bootstrap_equity_curves(trade_returns, n_paths=5000)
    dd_stats = mc_drawdown_stats(paths)
    sr_stats = mc_sharpe_distribution(trade_returns, n_paths=5000)
"""
from __future__ import annotations

import numpy as np


def bootstrap_equity_curves(
    trade_returns: np.ndarray | list[float],
    n_paths: int = 1000,
    n_trades: int | None = None,
    seed: int | None = 42,
) -> np.ndarray:
    """
    Generate Monte Carlo equity curve paths by bootstrapping trade returns.

    Each path is a random draw (with replacement) from the empirical trade
    return distribution — preserving marginal statistics but ignoring serial
    correlation.  For a serial-correlation–aware variant, see block-bootstrap.

    Parameters
    ----------
    trade_returns : 1-D array of per-trade fractional returns
    n_paths       : int — number of simulated paths
    n_trades      : int | None — length of each simulated path.
                    Defaults to len(trade_returns).
    seed          : int | None — RNG seed for reproducibility

    Returns
    -------
    np.ndarray of float, shape (n_paths, n_trades + 1).
    Row i contains the equity curve [1.0, 1+r1, (1+r1)(1+r2), ...].
    """
    trade_returns = np.asarray(trade_returns, dtype=float)
    trade_returns = trade_returns[np.isfinite(trade_returns)]
    if len(trade_returns) == 0:
        raise ValueError("trade_returns contains no finite values")

    if n_trades is None:
        n_trades = len(trade_returns)

    rng = np.random.default_rng(seed)
    # Shape: (n_paths, n_trades)
    sampled = rng.choice(trade_returns, size=(n_paths, n_trades), replace=True)

    # Equity curves: cumprod starting from 1.0
    equity = np.empty((n_paths, n_trades + 1), dtype=float)
    equity[:, 0] = 1.0
    equity[:, 1:] = np.cumprod(1.0 + sampled, axis=1)

    return equity


def _path_max_drawdown(equity: np.ndarray) -> np.ndarray:
    """Compute maximum drawdown for each row of an equity matrix."""
    running_max = np.maximum.accumulate(equity, axis=1)
    drawdowns = (running_max - equity) / running_max
    return drawdowns.max(axis=1)


def mc_drawdown_stats(paths: np.ndarray) -> dict:
    """
    Compute drawdown statistics across all Monte Carlo paths.

    Parameters
    ----------
    paths : np.ndarray shape (n_paths, n_trades + 1) — output of bootstrap_equity_curves

    Returns
    -------
    dict with keys:
        max_dd_p5   : float — 5th percentile max drawdown (best 95% case)
        max_dd_p50  : float — median max drawdown
        max_dd_p95  : float — 95th percentile max drawdown (worst 5% case)
        prob_ruin   : float — fraction of paths where equity ever falls below 0
        final_eq_p5 : float — 5th percentile of terminal equity
        final_eq_p50: float — median terminal equity
        final_eq_p95: float — 95th percentile terminal equity
        n_paths     : int   — number of simulated paths
    """
    max_dds = _path_max_drawdown(paths)
    final_eq = paths[:, -1]
    prob_ruin = float(np.mean(final_eq < 0.0))

    return {
        "max_dd_p5": float(np.percentile(max_dds, 5)),
        "max_dd_p50": float(np.percentile(max_dds, 50)),
        "max_dd_p95": float(np.percentile(max_dds, 95)),
        "prob_ruin": prob_ruin,
        "final_eq_p5": float(np.percentile(final_eq, 5)),
        "final_eq_p50": float(np.percentile(final_eq, 50)),
        "final_eq_p95": float(np.percentile(final_eq, 95)),
        "n_paths": int(len(paths)),
    }


def mc_sharpe_distribution(
    trade_returns: np.ndarray | list[float],
    n_paths: int = 1000,
    annualisation: float = 252.0,
    seed: int | None = 42,
) -> dict:
    """
    Bootstrap the Sharpe ratio distribution for a trading strategy.

    Parameters
    ----------
    trade_returns  : 1-D array of per-trade fractional returns
    n_paths        : int   — number of bootstrap samples
    annualisation  : float — trading days per year (252 for daily, adjust for intraday)
    seed           : int | None

    Returns
    -------
    dict with keys:
        sharpe_p5   : float — 5th percentile of bootstrapped Sharpe ratios
        sharpe_p50  : float — median
        sharpe_p95  : float — 95th percentile
        sharpe_mean : float — mean Sharpe across all paths
        n_paths     : int
    """
    trade_returns = np.asarray(trade_returns, dtype=float)
    trade_returns = trade_returns[np.isfinite(trade_returns)]
    rng = np.random.default_rng(seed)
    n = len(trade_returns)
    if n < 2:
        raise ValueError("Need at least 2 trade returns to compute Sharpe distribution")

    sharpes = np.empty(n_paths, dtype=float)
    for i in range(n_paths):
        sample = rng.choice(trade_returns, size=n, replace=True)
        std = float(np.std(sample, ddof=1))
        if std < 1e-12:
            sharpes[i] = 0.0
        else:
            sharpes[i] = float(np.mean(sample)) / std * np.sqrt(annualisation)

    return {
        "sharpe_p5": float(np.percentile(sharpes, 5)),
        "sharpe_p50": float(np.percentile(sharpes, 50)),
        "sharpe_p95": float(np.percentile(sharpes, 95)),
        "sharpe_mean": float(np.mean(sharpes)),
        "n_paths": n_paths,
    }


def mc_var_cvar(
    trade_returns: np.ndarray | list[float],
    confidence: float = 0.95,
    n_paths: int = 1000,
    seed: int | None = 42,
) -> dict:
    """
    Bootstrap Value-at-Risk and Conditional VaR (Expected Shortfall).

    Parameters
    ----------
    trade_returns : 1-D array of per-trade returns
    confidence    : float — VaR confidence level (e.g. 0.95 → 95% VaR)
    n_paths       : int   — bootstrap resamples
    seed          : int | None

    Returns
    -------
    dict with keys: var_pct, cvar_pct (in percentage of equity)
    """
    trade_returns = np.asarray(trade_returns, dtype=float)
    trade_returns = trade_returns[np.isfinite(trade_returns)]
    rng = np.random.default_rng(seed)
    n = len(trade_returns)

    final_returns = np.empty(n_paths, dtype=float)
    for i in range(n_paths):
        sample = rng.choice(trade_returns, size=n, replace=True)
        final_returns[i] = float(np.sum(sample))

    threshold = float(np.percentile(final_returns, (1 - confidence) * 100))
    cvar = float(np.mean(final_returns[final_returns <= threshold]))
    return {
        "var_pct": float(abs(threshold) * 100),
        "cvar_pct": float(abs(cvar) * 100),
        "confidence": confidence,
    }
