"""
Advanced evaluation metrics for the walk-forward training gate.

All functions operate on plain numpy arrays; no pandas dependency.
scipy.special.ndtr (normal CDF) is available transitively via scikit-learn.
"""
from __future__ import annotations

import math

import numpy as np


# ── Sortino Ratio ─────────────────────────────────────────────────────────────

def sortino_ratio(
    returns: np.ndarray, target: float = 0.0, annualisation: float = 252.0
) -> float:
    """
    Sortino ratio: mean excess return divided by downside deviation.
    Annualised by sqrt(annualisation).
    """
    mu = float(np.mean(returns)) - target
    downside = returns[returns < target]
    if len(downside) == 0:
        return float("inf") if mu > 0.0 else 0.0
    dd = float(np.std(downside, ddof=1))
    if dd < 1e-12:
        return float("inf") if mu > 0.0 else 0.0
    return float(mu / dd * math.sqrt(annualisation))


# ── Calmar Ratio ──────────────────────────────────────────────────────────────

def calmar_ratio(returns: np.ndarray, annualisation: float = 252.0) -> float:
    """Calmar ratio: annualised mean return / maximum drawdown."""
    cum = np.cumsum(returns)
    running_max = np.maximum.accumulate(cum)
    drawdowns = cum - running_max
    max_dd = float(abs(drawdowns.min())) if len(drawdowns) > 0 else 0.0
    ann_return = float(np.mean(returns)) * annualisation
    if max_dd < 1e-12:
        return float("inf") if ann_return > 0.0 else 0.0
    return ann_return / max_dd


# ── MAE / MFE / G-ratio ───────────────────────────────────────────────────────

def max_adverse_excursion(trade_returns: np.ndarray) -> dict:
    """
    MAE (mean worst loss per trade) and MFE (mean best gain per trade),
    summarised across all trades.

    G-ratio = MFE / MAE; values > 1 suggest favourable reward/risk.
    """
    mae = float(-np.mean(np.minimum(trade_returns, 0.0)))
    mfe = float(np.mean(np.maximum(trade_returns, 0.0)))
    g_ratio = mfe / mae if mae > 1e-12 else float("inf")
    return {
        "mae_mean": round(mae, 6),
        "mfe_mean": round(mfe, 6),
        "g_ratio": round(g_ratio if math.isfinite(g_ratio) else 0.0, 4),
    }


# ── Deflated Sharpe Ratio ─────────────────────────────────────────────────────

def deflated_sharpe_ratio(
    sharpe_observed: float,
    n_trials: int,
    n_obs: int,
    skewness: float = 0.0,
    excess_kurtosis: float = 0.0,
) -> float:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).
    Returns the probability that the true SR > 0 after correcting for
    multiple-testing selection bias and non-normality.

    Returns a value in [0, 1]; higher = more confidence the edge is real.
    """
    from scipy.special import ndtr  # available via scikit-learn

    if n_obs < 2 or n_trials < 1:
        return 0.0

    # Expected maximum SR from n_trials independent trials (Extreme Value approx)
    gamma = 0.5772156649  # Euler–Mascheroni constant
    if n_trials > 1:
        log2t = math.sqrt(2.0 * math.log(n_trials))
        sr_max = (1.0 - gamma) * log2t + gamma / log2t
    else:
        sr_max = 0.0

    # Standard error of the observed SR (adjusted for non-normality)
    var_sr = (
        1.0
        - skewness * sharpe_observed
        + (excess_kurtosis - 1.0) / 4.0 * sharpe_observed ** 2
    ) / (n_obs - 1)

    if var_sr <= 0.0:
        return 1.0 if sharpe_observed > sr_max else 0.0

    dsr_stat = (sharpe_observed - sr_max) / math.sqrt(var_sr)
    return float(ndtr(dsr_stat))


# ── Monte Carlo permutation test ──────────────────────────────────────────────

def monte_carlo_permutation_test(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.62,
    n_permutations: int = 500,
    seed: int = 42,
) -> dict:
    """
    Tests whether observed precision on active signals exceeds chance via
    label permutation.

    Returns:
      observed_precision   float
      null_precision_mean  float
      p_value              float   (fraction of permutations ≥ observed)
      significant          bool    (p_value < 0.05)
      n_permutations       int
    """
    rng = np.random.default_rng(seed)
    pred = (y_prob >= threshold).astype(int)
    active = pred == 1

    if int(active.sum()) == 0:
        return {
            "observed_precision": 0.0,
            "null_precision_mean": 0.0,
            "p_value": 1.0,
            "significant": False,
            "n_permutations": n_permutations,
        }

    observed_precision = float(np.mean(y_true[active]))
    null_precisions = np.empty(n_permutations)

    for i in range(n_permutations):
        shuffled = rng.permutation(y_true)
        null_precisions[i] = float(np.mean(shuffled[active]))

    p_value = float(np.mean(null_precisions >= observed_precision))

    return {
        "observed_precision": round(observed_precision, 4),
        "null_precision_mean": round(float(null_precisions.mean()), 4),
        "p_value": round(p_value, 4),
        "significant": bool(p_value < 0.05),
        "n_permutations": n_permutations,
    }


# ── Overnight swap cost model ─────────────────────────────────────────────────

def overnight_swap_cost(
    n_trades: int,
    hold_days_mean: float = 3.0,
    swap_per_lot_per_day: float = -0.85,
    lot_size: float = 0.1,
) -> dict:
    """
    Estimates total overnight (rollover) swap cost for a set of trades.
    swap_per_lot_per_day is negative for typical long FX major positions.
    """
    cost_per_trade = swap_per_lot_per_day * hold_days_mean * lot_size
    total_cost = cost_per_trade * n_trades
    return {
        "hold_days_mean": hold_days_mean,
        "swap_per_lot_per_day_usd": swap_per_lot_per_day,
        "lot_size": lot_size,
        "cost_per_trade_usd": round(cost_per_trade, 4),
        "total_swap_cost_usd": round(total_cost, 2),
        "n_trades": n_trades,
    }


# ── Composite advanced gate ───────────────────────────────────────────────────

def evaluate_advanced_gates(
    returns: np.ndarray,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.62,
    n_trials: int = 5,
    n_permutations: int = 500,
) -> dict:
    """
    Run the full set of P1 advanced gate metrics.

    Returns a structured dict suitable for inclusion in training_report.json.
    gate_pass is True when DSR ≥ 0.95, permutation test is significant,
    and Sortino ratio > 0.5.
    """
    import pandas as pd  # only used for skew/kurtosis

    sortino = sortino_ratio(returns)
    calmar = calmar_ratio(returns)
    mae_mfe = max_adverse_excursion(returns)

    ret_std = float(np.std(returns, ddof=1))
    sharpe = (
        float(np.mean(returns) / ret_std * math.sqrt(252.0))
        if ret_std > 1e-12
        else 0.0
    )

    ret_s = pd.Series(returns)
    skewness = float(ret_s.skew()) if len(returns) > 2 else 0.0
    excess_kurt = float(ret_s.kurtosis()) if len(returns) > 3 else 0.0

    dsr = deflated_sharpe_ratio(
        sharpe_observed=sharpe,
        n_trials=n_trials,
        n_obs=len(returns),
        skewness=skewness,
        excess_kurtosis=excess_kurt,
    )

    perm = monte_carlo_permutation_test(
        y_true, y_prob, threshold=threshold, n_permutations=n_permutations
    )

    n_signals = int((y_prob >= threshold).sum())
    swap = overnight_swap_cost(n_trades=n_signals)

    def _safe(v: float) -> float:
        return round(v if math.isfinite(v) else 0.0, 4)

    return {
        "sortino_ratio": _safe(sortino),
        "calmar_ratio": _safe(calmar),
        "sharpe_ratio": round(sharpe, 4),
        "deflated_sharpe_ratio": round(dsr, 4),
        "mae_mfe": mae_mfe,
        "permutation_test": perm,
        "swap_cost_estimate": swap,
        "gate_pass": bool(
            dsr >= 0.95 and perm["significant"] and sortino > 0.5
        ),
    }
