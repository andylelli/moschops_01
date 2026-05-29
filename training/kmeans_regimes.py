"""
K-means clustering regime detection.

Clusters market observations into discrete regimes using K-means on a feature
vector (typically returns + volatility + trend-strength features).

Regimes are labelled 0…n_clusters-1 and sorted by mean return so that
label semantics are consistent across runs.

Usage:
    from kmeans_regimes import fit_kmeans_regimes, kmeans_regime_feature

    model, labels = fit_kmeans_regimes(df, feature_cols=["return","vol"], n_clusters=3)
    df = kmeans_regime_feature(df, feature_cols=["return","vol"], n_clusters=3)
    # df now has a 'kmeans_regime' column
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def fit_kmeans_regimes(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    n_clusters: int = 3,
    random_state: int = 42,
    n_init: int = 10,
) -> tuple["KMeans", np.ndarray]:
    """
    Fit K-means on the selected feature columns and return (model, labels).

    Labels are re-mapped so that cluster 0 has the lowest mean 1-bar log-return
    and cluster n_clusters-1 has the highest (requires 'close' or 'return' in df
    or feature_cols to enable sorting; otherwise labels are sorted by cluster
    centroid L2 norm).

    Parameters
    ----------
    df           : pd.DataFrame with feature columns
    feature_cols : list of column names to cluster on.
                   Defaults to log-return + rolling-volatility if None.
    n_clusters   : int — number of clusters / regimes
    random_state : int — reproducibility seed
    n_init       : int — number of K-means initialisations

    Returns
    -------
    (fitted KMeans, np.ndarray of int labels shape (n,))
    """
    if feature_cols is None:
        # Build default features: log-return + 10-bar rolling std
        if "close" not in df.columns:
            raise ValueError("feature_cols is None but 'close' column not found.")
        log_ret = np.log(df["close"] / df["close"].shift(1)).fillna(0.0)
        vol = log_ret.rolling(10, min_periods=2).std().fillna(log_ret.std())
        X_df = pd.DataFrame({"return": log_ret, "vol": vol})
        feature_cols = ["return", "vol"]
    else:
        X_df = df[feature_cols]

    X = X_df.dropna().to_numpy(dtype=float)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=n_init)
    raw_labels = model.fit_predict(X_scaled)

    # Re-label clusters by ascending mean return of the first feature column
    mean_per_cluster = [
        float(np.mean(X[raw_labels == k, 0])) for k in range(n_clusters)
    ]
    order = np.argsort(mean_per_cluster)
    remap = {int(old): int(new) for new, old in enumerate(order)}
    labels = np.array([remap[int(l)] for l in raw_labels], dtype=int)

    # Pad with NaN-derived rows that were dropped (len(labels) == len(X_df.dropna()))
    full_labels = np.full(len(df), np.nan)
    valid_idx = X_df.dropna().index
    # Map valid_idx positions back to df integer positions
    idx_positions = df.index.get_indexer(valid_idx)
    full_labels[idx_positions[idx_positions >= 0]] = labels

    # Store scaler on model for later use
    model.feature_scaler_ = scaler  # type: ignore[attr-defined]
    model.feature_cols_ = feature_cols  # type: ignore[attr-defined]

    return model, full_labels.astype(float)


def kmeans_regime_feature(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    n_clusters: int = 3,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Fit K-means and add a 'kmeans_regime' integer column to df.

    Returns a copy of df.
    """
    df = df.copy()
    _, labels = fit_kmeans_regimes(
        df, feature_cols=feature_cols, n_clusters=n_clusters, random_state=random_state
    )
    df["kmeans_regime"] = labels
    return df


def predict_regime(
    model: "KMeans",
    df: pd.DataFrame,
) -> np.ndarray:
    """
    Assign regimes to new bars using a previously fitted K-means model.

    Parameters
    ----------
    model : KMeans — fitted by fit_kmeans_regimes (must have feature_scaler_ and feature_cols_)
    df    : pd.DataFrame — new bars with the same feature columns

    Returns
    -------
    np.ndarray of int regime labels, shape (n,).
    """
    feature_cols = model.feature_cols_  # type: ignore[attr-defined]
    scaler = model.feature_scaler_  # type: ignore[attr-defined]
    X = df[feature_cols].fillna(0.0).to_numpy(dtype=float)
    X_scaled = scaler.transform(X)
    return model.predict(X_scaled).astype(int)
