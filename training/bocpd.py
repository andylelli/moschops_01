"""
Bayesian Online Changepoint Detection (BOCPD).

Implements the Adams & MacKay (2007) algorithm with:
- Gaussian observations
- Normal-Inverse-Gamma conjugate prior
- Constant hazard function (Poisson process changepoints)

Per-bar posterior probability P(r_t = 0 | x_{1:t}) is the probability that
a changepoint occurred at bar t.  A spike in this value indicates a regime shift.

Reference:
    Adams, R.P. & MacKay, D.J.C. (2007). Bayesian Online Changepoint Detection.
    arXiv:0710.3742
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def bocpd_changepoint_probs(
    series: pd.Series | np.ndarray,
    hazard_lambda: float = 250.0,
    kappa_0: float = 1.0,
    mu_0: float | None = None,
    alpha_0: float = 1.0,
    beta_0: float | None = None,
    max_run_length: int = 500,
) -> np.ndarray:
    """
    Run BOCPD and return per-bar posterior probability of a changepoint.

    Parameters
    ----------
    series          : 1-D time series (log-returns recommended)
    hazard_lambda   : float — expected run length between changepoints (bars)
    kappa_0         : float — prior pseudo-count for mean estimation
    mu_0            : float | None — prior mean; defaults to sample mean of first 20 bars
    alpha_0         : float — prior shape for variance (IG)
    beta_0          : float | None — prior scale for variance; defaults to sample variance
    max_run_length  : int   — truncate run-length distribution to this maximum
                              to bound memory use (older hypotheses are collapsed)

    Returns
    -------
    np.ndarray of float in [0, 1], shape (n,).
    Higher values indicate a likely changepoint at that bar.
    """
    from scipy.stats import t as student_t  # noqa: PLC0415 — scipy via sklearn

    x = np.asarray(series, dtype=float)
    n = len(x)
    warmup = min(20, n)

    if mu_0 is None:
        mu_0 = float(np.nanmean(x[:warmup]))
    if beta_0 is None:
        beta_0 = float(np.nanvar(x[:warmup]) + 1e-6)

    hazard = 1.0 / hazard_lambda

    # State: per-run-length-hypothesis (R_r, kappa_r, mu_r, alpha_r, beta_r)
    R = np.array([1.0])
    kappas = np.array([kappa_0])
    mus = np.array([mu_0])
    alphas = np.array([alpha_0])
    betas = np.array([beta_0])

    cp_probs = np.zeros(n)

    for t in range(n):
        xt = x[t]

        if not np.isfinite(xt):
            cp_probs[t] = np.nan
            # Prepend prior for new run-length = 0 without updating existing hypotheses
            kappas = np.concatenate([[kappa_0], kappas])
            mus = np.concatenate([[mu_0], mus])
            alphas = np.concatenate([[alpha_0], alphas])
            betas = np.concatenate([[beta_0], betas])
            R = np.concatenate([[hazard], R * (1.0 - hazard)])
            R /= R.sum() + 1e-300
            _truncate(R, kappas, mus, alphas, betas, max_run_length)
            continue

        # Predictive: Student-t(2α, μ, β(κ+1)/(ακ))
        nu = 2.0 * alphas
        scale2 = betas * (kappas + 1.0) / (alphas * kappas)
        scale2 = np.maximum(scale2, 1e-12)
        log_pred = student_t.logpdf(xt, df=nu, loc=mus, scale=np.sqrt(scale2))

        # Numerically stable predictive weights
        log_pred -= log_pred.max()
        pred_w = np.exp(log_pred)

        # New probabilities
        R_new = np.empty(len(R) + 1)
        R_new[0] = np.sum(R * hazard * pred_w)          # changepoint
        R_new[1:] = R * (1.0 - hazard) * pred_w         # growth

        total = R_new.sum()
        R_new /= total if total > 1e-300 else 1.0

        cp_probs[t] = float(R_new[0])

        # NIG conjugate update: new r=0 gets prior; old r→r+1 gets posterior
        kappas_new = np.concatenate([[kappa_0], kappas + 1.0])
        mus_new = np.concatenate([[mu_0], (kappas * mus + xt) / (kappas + 1.0)])
        alphas_new = np.concatenate([[alpha_0], alphas + 0.5])
        delta = xt - mus
        betas_new = np.concatenate([[beta_0], betas + 0.5 * kappas * delta**2 / (kappas + 1.0)])

        R = R_new
        kappas, mus, alphas, betas = kappas_new, mus_new, alphas_new, betas_new

        # Truncate low-probability long run lengths
        if len(R) > max_run_length:
            R = R[:max_run_length]
            kappas = kappas[:max_run_length]
            mus = mus[:max_run_length]
            alphas = alphas[:max_run_length]
            betas = betas[:max_run_length]
            R /= R.sum() + 1e-300

    return cp_probs


def _truncate(R, kappas, mus, alphas, betas, max_run_length: int) -> None:
    """In-place truncation to max_run_length (operates on mutable view — no-op here)."""
    # Arrays are passed by reference; truncation happens in the caller via slice.


def bocpd_changepoint_feature(
    df: pd.DataFrame,
    price_col: str = "close",
    hazard_lambda: float = 250.0,
    max_run_length: int = 500,
) -> pd.DataFrame:
    """
    Compute log returns, run BOCPD, and add a 'bocpd_cp_prob' column to df.

    Returns a copy of df.
    """
    df = df.copy()
    log_ret = np.log(df[price_col] / df[price_col].shift(1)).fillna(0.0)
    df["bocpd_cp_prob"] = bocpd_changepoint_probs(
        log_ret, hazard_lambda=hazard_lambda, max_run_length=max_run_length
    )
    return df
