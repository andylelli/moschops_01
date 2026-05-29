"""
Data quality checks, ADF stationarity reporting, and feature winsorisation.

All functions are stateless and operate on pandas DataFrames.
statsmodels is a lazy import so this module loads without it installed;
check_stationarity() returns an error dict if it is missing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── Bar quality validation ────────────────────────────────────────────────────

def validate_bars(df: pd.DataFrame) -> dict:
    """
    OHLCV integrity checks.

    Returns a dict:
      total_bars        int
      quality_issues    list[str]   — human-readable issue descriptions
      is_clean          bool        — True when quality_issues is empty
      nan_counts        dict[str, int]  — columns with NaN values
      total_nans        int
    """
    issues: list[str] = []

    ohlc = [c for c in ("open", "high", "low", "close") if c in df.columns]

    # OHLC integrity
    if "high" in df.columns and "low" in df.columns:
        n = int((df["high"] < df["low"]).sum())
        if n:
            issues.append(f"high < low on {n} bars")

    if "open" in df.columns and "high" in df.columns:
        n = int((df["open"] > df["high"]).sum())
        if n:
            issues.append(f"open > high on {n} bars")

    if "open" in df.columns and "low" in df.columns:
        n = int((df["open"] < df["low"]).sum())
        if n:
            issues.append(f"open < low on {n} bars")

    # Non-positive prices
    for col in ohlc:
        n = int((df[col] <= 0).sum())
        if n:
            issues.append(f"{col} <= 0 on {n} bars")

    # Duplicate timestamps
    if isinstance(df.index, pd.DatetimeIndex):
        n = int(df.index.duplicated().sum())
        if n:
            issues.append(f"{n} duplicate timestamps")

    nan_counts = {
        k: int(v) for k, v in df.isna().sum().items() if v > 0
    }

    return {
        "total_bars": len(df),
        "quality_issues": issues,
        "is_clean": len(issues) == 0,
        "nan_counts": nan_counts,
        "total_nans": sum(nan_counts.values()),
    }


# ── ADF stationarity ──────────────────────────────────────────────────────────

def check_stationarity(
    df: pd.DataFrame,
    feature_cols: list[str],
    significance: float = 0.05,
) -> dict:
    """
    Augmented Dickey–Fuller test per feature column.

    Returns:
      feature_results        dict[str, dict]  — per-feature ADF stats
      non_stationary_features  list[str]
      all_stationary         bool
      error                  str   (only present if statsmodels is missing)
    """
    try:
        from statsmodels.tsa.stattools import adfuller  # type: ignore[import]
    except ImportError:
        return {"error": "statsmodels not installed — run: pip install 'statsmodels>=0.14.0'"}

    results: dict[str, dict] = {}
    for col in feature_cols:
        if col not in df.columns:
            results[col] = {"stationary": None, "p_value": None, "note": "column missing"}
            continue

        series = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) < 20:
            results[col] = {
                "stationary": None,
                "p_value": None,
                "note": f"too few observations ({len(series)})",
            }
            continue

        try:
            adf_stat, p_value, _, _, crit_vals, _ = adfuller(series, autolag="AIC")
            results[col] = {
                "stationary": bool(p_value < significance),
                "p_value": round(float(p_value), 4),
                "adf_statistic": round(float(adf_stat), 4),
                "critical_1pct": round(float(crit_vals["1%"]), 4),
            }
        except Exception as exc:
            results[col] = {"stationary": None, "p_value": None, "note": str(exc)}

    non_stationary = [k for k, v in results.items() if v.get("stationary") is False]

    return {
        "feature_results": results,
        "non_stationary_features": non_stationary,
        "all_stationary": len(non_stationary) == 0,
    }


# ── Winsorisation ─────────────────────────────────────────────────────────────

def winsorise_features(
    df: pd.DataFrame,
    feature_cols: list[str],
    lower_pct: float = 1.0,
    upper_pct: float = 99.0,
) -> tuple[pd.DataFrame, dict]:
    """
    Clip each feature to its [lower_pct, upper_pct] percentile range.

    Returns:
      df_copy        DataFrame with clipped columns
      clips_applied  dict[str, dict] — columns where clipping had effect
    """
    df = df.copy()
    clips_applied: dict[str, dict] = {}

    for col in feature_cols:
        if col not in df.columns:
            continue
        series = df[col].replace([np.inf, -np.inf], np.nan)
        valid = series.dropna()
        if len(valid) == 0:
            continue

        lo = float(np.percentile(valid, lower_pct))
        hi = float(np.percentile(valid, upper_pct))

        clipped = series.clip(lo, hi)
        n_clipped = int((series.dropna() != clipped.dropna()).sum())
        df[col] = clipped
        if n_clipped > 0:
            clips_applied[col] = {
                "lo": round(lo, 8),
                "hi": round(hi, 8),
                "n_clipped": n_clipped,
            }

    return df, clips_applied
