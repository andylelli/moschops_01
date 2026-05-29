"""
Feature quality auditing and concept drift detection.

Implements:
- feature_correlation_matrix : Pearson correlation matrix + high-corr pair detection
- psi                        : Population Stability Index for one feature
- concept_drift_report       : per-feature PSI report with overall drift flag

No external dependencies beyond numpy and pandas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def feature_correlation_matrix(
    df: pd.DataFrame,
    feature_cols: list[str],
    high_corr_threshold: float = 0.85,
) -> dict:
    """
    Compute Pearson correlation matrix and identify highly correlated feature pairs.

    Parameters
    ----------
    df                  : pd.DataFrame containing the feature columns
    feature_cols        : list of column names to include in the audit
    high_corr_threshold : float — absolute correlation above which a pair is flagged

    Returns
    -------
    dict:
        feature_names    : list[str]
        corr_matrix      : list[list[float]] — full n×n correlation matrix
        high_corr_pairs  : list of {feature_a, feature_b, correlation}
                           for all pairs with |corr| ≥ threshold
        max_corr         : float — maximum absolute off-diagonal correlation
    """
    sub = df[feature_cols].dropna()
    corr = sub.corr()
    n = len(feature_cols)

    high_pairs: list[dict] = []
    for i in range(n):
        for j in range(i + 1, n):
            val = float(corr.iloc[i, j])
            if np.isfinite(val) and abs(val) >= high_corr_threshold:
                high_pairs.append({
                    "feature_a": feature_cols[i],
                    "feature_b": feature_cols[j],
                    "correlation": round(val, 4),
                })

    off_diag_vals = [
        abs(float(corr.iloc[i, j]))
        for i in range(n)
        for j in range(n)
        if i != j and np.isfinite(corr.iloc[i, j])
    ]
    max_corr = float(max(off_diag_vals)) if off_diag_vals else 0.0

    return {
        "feature_names": feature_cols,
        "corr_matrix": corr.values.tolist(),
        "high_corr_pairs": high_pairs,
        "max_corr": round(max_corr, 4),
    }


def psi(
    expected: np.ndarray | pd.Series,
    actual: np.ndarray | pd.Series,
    n_bins: int = 10,
    eps: float = 1e-6,
) -> float:
    """
    Population Stability Index between a reference and a current distribution.

    Bins are determined by quantiles of the expected (reference) distribution
    so that each reference bin contains roughly equal probability mass.

    Interpretation:
        PSI < 0.10  → stable (no action needed)
        PSI 0.10–0.25 → moderate shift (monitor)
        PSI > 0.25  → significant shift (likely concept drift)

    Parameters
    ----------
    expected : reference distribution (e.g. training-set feature values)
    actual   : current distribution  (e.g. live/test-set feature values)
    n_bins   : int   — number of histogram bins
    eps      : float — floor to prevent log(0)

    Returns
    -------
    float PSI score (≥ 0).
    """
    exp_arr = np.asarray(expected, dtype=float)
    act_arr = np.asarray(actual, dtype=float)

    quantiles = np.linspace(0, 100, n_bins + 1)
    breakpoints = np.unique(np.percentile(exp_arr[np.isfinite(exp_arr)], quantiles))

    if len(breakpoints) < 2:
        return 0.0

    exp_counts, _ = np.histogram(exp_arr, bins=breakpoints)
    act_counts, _ = np.histogram(act_arr, bins=breakpoints)

    exp_pct = np.clip(exp_counts / (exp_counts.sum() + eps), eps, None)
    act_pct = np.clip(act_counts / (act_counts.sum() + eps), eps, None)

    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def concept_drift_report(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: list[str],
    threshold: float = 0.2,
    n_bins: int = 10,
) -> dict:
    """
    Compute PSI for each feature and produce an overall drift assessment.

    Parameters
    ----------
    reference_df : DataFrame from the training / reference period
    current_df   : DataFrame from the live / recent period
    feature_cols : list of feature column names to test
    threshold    : float — PSI above which a feature is considered drifted
    n_bins       : int   — histogram bins for PSI

    Returns
    -------
    dict:
        feature_psi      : {feature: psi_score}  (NaN if data unavailable)
        drifted_features : list of features with PSI > threshold
        drift_detected   : bool — True if any feature PSI > threshold
        max_psi          : float
        threshold        : float
    """
    feature_psi: dict[str, float] = {}

    for col in feature_cols:
        missing = col not in reference_df.columns or col not in current_df.columns
        if missing:
            feature_psi[col] = float("nan")
            continue
        ref_vals = reference_df[col].dropna().to_numpy()
        cur_vals = current_df[col].dropna().to_numpy()
        if len(ref_vals) < 5 or len(cur_vals) < 5:
            feature_psi[col] = float("nan")
            continue
        feature_psi[col] = round(psi(ref_vals, cur_vals, n_bins=n_bins), 4)

    drifted = [
        f for f, v in feature_psi.items() if np.isfinite(v) and v > threshold
    ]
    finite_vals = [v for v in feature_psi.values() if np.isfinite(v)]
    max_psi = float(max(finite_vals)) if finite_vals else 0.0

    return {
        "feature_psi": feature_psi,
        "drifted_features": drifted,
        "drift_detected": len(drifted) > 0,
        "max_psi": round(max_psi, 4),
        "threshold": threshold,
    }
