"""
Variable spread simulation for realistic backtesting.

In live forex/CFD trading the spread is not constant; it widens around:
- Scheduled news events (NFP, FOMC, CPI releases)
- Market open / close transitions
- Overnight / rollover periods
- Low-liquidity windows

This module lets you inject realistic spread variability into a backtest so
that cost estimates match live-execution conditions.

Usage:
    from spread_sim import simulate_spread, apply_spread_costs, spread_cost_report

    spreads = simulate_spread(n_bars=5000, base_spread_pips=1.5,
                              news_indices=[100, 500, 1200])
    net_returns = apply_spread_costs(trade_returns, spreads,
                                     lot_size=0.1, pip_value=10.0)
    report = spread_cost_report(trade_returns, spreads, lot_size=0.1, pip_value=10.0)
"""
from __future__ import annotations

from typing import Sequence

import numpy as np


def simulate_spread(
    n_bars: int,
    base_spread_pips: float = 1.5,
    news_indices: Sequence[int] | None = None,
    news_bars: int = 6,
    news_multiplier: float = 4.0,
    overnight_indices: Sequence[int] | None = None,
    overnight_bars: int = 3,
    overnight_multiplier: float = 2.0,
    noise_std_pips: float = 0.2,
    seed: int | None = None,
) -> np.ndarray:
    """
    Generate a per-bar spread array (in pips).

    Parameters
    ----------
    n_bars             : int   — number of bars to simulate
    base_spread_pips   : float — median spread during normal market hours
    news_indices       : list[int] | None — bar indices at which news events begin
    news_bars          : int   — how many bars after a news event the spread stays wide
    news_multiplier    : float — spread multiplier during news windows
    overnight_indices  : list[int] | None — bar indices of overnight / rollover bars
    overnight_bars     : int   — width of the overnight window
    overnight_multiplier: float — spread multiplier during overnight windows
    noise_std_pips     : float — Gaussian noise std added to each bar (log-scale)
    seed               : int | None — RNG seed for reproducibility

    Returns
    -------
    np.ndarray of float shape (n_bars,) — spread in pips per bar
    """
    rng = np.random.default_rng(seed)
    spreads = np.full(n_bars, base_spread_pips, dtype=float)

    # Add log-normal noise so spread is always positive
    if noise_std_pips > 0:
        noise = rng.normal(0.0, noise_std_pips / base_spread_pips, n_bars)
        spreads = spreads * np.exp(noise)

    # Apply news event widening
    if news_indices:
        for idx in news_indices:
            for b in range(max(0, idx), min(n_bars, idx + news_bars)):
                spreads[b] = max(spreads[b], base_spread_pips * news_multiplier)

    # Apply overnight / rollover widening
    if overnight_indices:
        for idx in overnight_indices:
            for b in range(max(0, idx), min(n_bars, idx + overnight_bars)):
                spreads[b] = max(spreads[b], base_spread_pips * overnight_multiplier)

    return spreads


def apply_spread_costs(
    trade_returns: np.ndarray | list[float],
    spreads_pips: np.ndarray | list[float],
    lot_size: float = 0.1,
    pip_value: float = 10.0,
    pip_size: float = 0.0001,
    account_currency_equity: float = 10_000.0,
) -> np.ndarray:
    """
    Deduct spread cost from each trade return.

    The spread cost for one round-trip trade is:
        cost = spread_pips × pip_value × lot_size

    Expressed as a fraction of account equity:
        cost_pct = cost / account_currency_equity

    Parameters
    ----------
    trade_returns             : array-like — raw fractional returns per trade
    spreads_pips              : array-like — spread in pips at entry bar for each trade
    lot_size                  : float — lot size in standard lots
    pip_value                 : float — monetary value of 1 pip per standard lot (e.g. $10)
    pip_size                  : float — price increment per pip (0.0001 for majors, 0.01 for JPY)
    account_currency_equity   : float — account equity in account currency

    Returns
    -------
    np.ndarray of net fractional returns (same length as trade_returns)
    """
    trade_returns = np.asarray(trade_returns, dtype=float)
    spreads_pips = np.asarray(spreads_pips, dtype=float)
    if len(spreads_pips) != len(trade_returns):
        raise ValueError("trade_returns and spreads_pips must have the same length")
    cost_per_trade = spreads_pips * pip_value * lot_size / account_currency_equity
    return trade_returns - cost_per_trade


def spread_cost_report(
    trade_returns: np.ndarray | list[float],
    spreads_pips: np.ndarray | list[float],
    lot_size: float = 0.1,
    pip_value: float = 10.0,
    account_currency_equity: float = 10_000.0,
) -> dict:
    """
    Summarise the impact of spread costs on backtest performance.

    Returns
    -------
    dict with keys:
        n_trades          : int   — number of trades
        mean_spread_pips  : float — average spread per trade
        total_cost_pct    : float — total spread cost as % of equity
        gross_pnl_pct     : float — sum of raw returns (% equity)
        net_pnl_pct       : float — sum after spread deduction (% equity)
        cost_drag_pct     : float — cost_total / abs(gross_pnl) if gross_pnl != 0
    """
    trade_returns = np.asarray(trade_returns, dtype=float)
    spreads_pips = np.asarray(spreads_pips, dtype=float)
    net_returns = apply_spread_costs(
        trade_returns, spreads_pips, lot_size=lot_size,
        pip_value=pip_value, account_currency_equity=account_currency_equity,
    )
    cost_per_trade = trade_returns - net_returns
    total_cost = float(np.sum(cost_per_trade))
    gross_pnl = float(np.sum(trade_returns))
    net_pnl = float(np.sum(net_returns))
    cost_drag = total_cost / abs(gross_pnl) if abs(gross_pnl) > 1e-10 else np.nan

    return {
        "n_trades": int(len(trade_returns)),
        "mean_spread_pips": float(np.mean(spreads_pips)),
        "total_cost_pct": float(total_cost * 100),
        "gross_pnl_pct": float(gross_pnl * 100),
        "net_pnl_pct": float(net_pnl * 100),
        "cost_drag_pct": float(cost_drag * 100) if np.isfinite(cost_drag) else None,
    }
