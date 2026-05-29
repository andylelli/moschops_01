"""
Labeling utilities for financial ML.

Implements:
- Triple barrier labeling (de Prado, Advances in Financial Machine Learning Ch. 3)
- CUSUM-filtered event sampling

All functions operate on pandas Series/DataFrames and do not modify any
existing training scripts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def triple_barrier_label(
    close: pd.Series,
    tp_pct: float = 0.015,
    sl_pct: float = 0.010,
    max_bars: int = 20,
) -> pd.Series:
    """
    Apply triple-barrier labeling to a close price series.

    For each bar i, the label is determined by which barrier is first touched
    within [i+1, i+max_bars]:
      +1  → take-profit (upper barrier) touched first
      -1  → stop-loss  (lower barrier) touched first
       0  → neither barrier touched within max_bars (time barrier)

    The last max_bars entries are NaN (insufficient lookahead).

    Parameters
    ----------
    close    : pd.Series — close prices, oldest → newest
    tp_pct   : float    — take-profit distance as a fraction of entry (e.g. 0.015 = 1.5 %)
    sl_pct   : float    — stop-loss distance as a fraction of entry   (e.g. 0.010 = 1.0 %)
    max_bars : int      — maximum holding period in bars (time barrier)

    Returns
    -------
    pd.Series of float {-1.0, 0.0, 1.0, NaN} with the same index as close.
    """
    n = len(close)
    labels = np.full(n, np.nan)
    prices = close.to_numpy(dtype=float)

    for i in range(n - max_bars):
        entry = prices[i]
        if not np.isfinite(entry) or entry <= 0:
            continue
        upper = entry * (1.0 + tp_pct)
        lower = entry * (1.0 - sl_pct)
        outcome = 0
        for j in range(i + 1, min(i + max_bars + 1, n)):
            if prices[j] >= upper:
                outcome = 1
                break
            if prices[j] <= lower:
                outcome = -1
                break
        labels[i] = float(outcome)

    return pd.Series(labels, index=close.index, name="triple_barrier_label")


def cusum_events(
    close: pd.Series,
    h: float | None = None,
    h_lookback: int = 20,
) -> pd.Index:
    """
    CUSUM filter: identifies bars where accumulated signed drift exceeds threshold h.
    Returns the index labels of sampled event bars.

    If h is None the threshold is set adaptively to the rolling standard deviation
    of log-returns over h_lookback bars (one standard deviation per bar).

    Parameters
    ----------
    close      : pd.Series — close prices
    h          : float | None — fixed threshold; None → adaptive (rolling std)
    h_lookback : int — lookback window for adaptive threshold

    Returns
    -------
    pd.Index of selected event bar labels.
    """
    log_ret = np.log(close / close.shift(1)).fillna(0.0)
    n = len(close)

    if h is None:
        thresholds = log_ret.rolling(h_lookback, min_periods=h_lookback).std().fillna(log_ret.std())
    else:
        thresholds = pd.Series(np.full(n, float(h)), index=close.index)

    s_pos = 0.0
    s_neg = 0.0
    events: list = []
    ret_arr = log_ret.to_numpy(dtype=float)
    thr_arr = thresholds.to_numpy(dtype=float)

    for i in range(1, n):
        s_pos = max(0.0, s_pos + ret_arr[i])
        s_neg = max(0.0, s_neg - ret_arr[i])
        thr = thr_arr[i]
        if not np.isfinite(thr) or thr <= 0:
            continue
        if s_pos >= thr:
            s_pos = 0.0
            events.append(close.index[i])
        elif s_neg >= thr:
            s_neg = 0.0
            events.append(close.index[i])

    return pd.Index(events)
