"""
Automated retraining pipeline.

Orchestrates the full model refresh cycle:
    1. Decide whether retraining is needed (time-based or alert-based)
    2. Fetch historical OHLCV bars from the backend REST API
    3. Compute P1 features via features.build_feature_set()
    4. Data quality gates via quality.validate_bars()
    5. Walk-forward training with expanding-window CV
    6. Advanced gate evaluation via metrics.evaluate_advanced_gates()
    7. Compare new model vs current; promote if gates pass and AUC improves
    8. Write retrain_report.json to output_dir

Usage:
    from retrain_pipeline import RetrainConfig, should_retrain, run_retrain

    cfg = RetrainConfig(
        backend_url="http://localhost:3000",
        symbol="EURUSD",
        timeframe="H1",
        output_dir="models",
    )
    needs_retrain = should_retrain(last_train_date="2024-01-01", monitoring_alert=None, cfg=cfg)
    if needs_retrain:
        result = run_retrain(cfg)
        print(result["status"], result["promoted"])

Dependencies:
    - requests          : lazy import (for backend API calls)
    - training/features : build_feature_set
    - training/quality  : validate_bars
    - training/metrics  : evaluate_advanced_gates
    - training/cv       : ExpandingWindowCV  (P2 module)
    - sklearn           : LogisticRegression, cross_val_predict
    - skl2onnx          : lazy import (ONNX export)
"""
from __future__ import annotations

import json
import logging
import pathlib
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

_log = logging.getLogger("training.retrain_pipeline")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class RetrainConfig:
    """
    Configuration for one automated retraining run.

    Attributes
    ----------
    retrain_interval_days : int   — minimum calendar days between retrains
    min_new_bars          : int   — minimum bars needed to trigger a retrain
    gate_auc_min          : float — minimum mean OOS AUC across CV folds
    gate_brier_max        : float — maximum mean OOS Brier score
    model_name            : str   — base name for saved model files
    cv_folds              : int   — number of expanding-window CV folds
    output_dir            : str   — directory to write model files and reports
    backend_url           : str   — base URL of the Fastify backend API
    symbol                : str   — FX symbol (e.g. "EURUSD")
    timeframe             : str   — bar timeframe (e.g. "H1")
    n_bars                : int   — number of bars to fetch from backend
    promote_if_better     : bool  — auto-promote when new AUC > current AUC
    """

    retrain_interval_days: int = 7
    min_new_bars: int = 500
    gate_auc_min: float = 0.52
    gate_brier_max: float = 0.25
    model_name: str = "daily_breakout_model"
    cv_folds: int = 5
    output_dir: str = "models"
    backend_url: str = "http://localhost:3000"
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    n_bars: int = 5000
    promote_if_better: bool = True


# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------

def should_retrain(
    last_train_date: Optional[str],
    monitoring_alert: Optional[dict],
    cfg: RetrainConfig,
) -> bool:
    """
    Decide whether a retraining run should be triggered.

    Returns True if any of the following:
    - last_train_date is None (never trained)
    - Enough calendar days have elapsed since last training
    - monitoring_alert is not None and indicates drift / degradation

    Parameters
    ----------
    last_train_date  : str | None — ISO date string "YYYY-MM-DD" of last training
    monitoring_alert : dict | None — alert dict from monitoring.check_performance_drift
    cfg              : RetrainConfig

    Returns
    -------
    bool
    """
    if last_train_date is None:
        return True

    try:
        last_dt = datetime.fromisoformat(last_train_date.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return True

    today = datetime.now(tz=timezone.utc).date()
    days_elapsed = (today - last_dt).days

    if days_elapsed >= cfg.retrain_interval_days:
        return True

    if monitoring_alert is not None:
        status = monitoring_alert.get("status", "ok")
        if status in ("drift_detected", "degraded", "critical"):
            return True

    return False


def load_current_metrics(output_dir: str) -> dict:
    """
    Load metrics from the current production model's training_report.json.

    Returns an empty dict if the report does not exist.
    """
    report_path = pathlib.Path(output_dir) / "training_report.json"
    if not report_path.exists():
        return {}
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_bars(cfg: RetrainConfig) -> pd.DataFrame:
    """
    Fetch OHLCV bars from the backend REST API.

    Endpoint: GET /historical-data/bars?symbol=&timeframe=&limit=
    Expected JSON: [{open, high, low, close, volume, time}, ...]

    Falls back to an empty DataFrame if requests is unavailable or the
    request fails.
    """
    try:
        import requests  # noqa: PLC0415 — lazy import
    except ImportError:
        warnings.warn("requests not installed; cannot fetch bars from backend", stacklevel=2)
        _log.warning("requests not installed; cannot fetch bars from backend")
        return pd.DataFrame()

    url = f"{cfg.backend_url.rstrip('/')}/historical-data/bars"
    params = {
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "limit": cfg.n_bars,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        warnings.warn(f"Failed to fetch bars from backend: {exc}", stacklevel=2)
        _log.warning("failed to fetch bars from backend: %s", exc)
        return pd.DataFrame()

    # Support both {"bars": [...]} and direct [...]
    if isinstance(data, dict):
        data = data.get("bars", data.get("data", []))

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    # Normalise column names
    rename_map = {
        "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
        "t": "time", "timestamp": "time",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
        df.sort_values("time", inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------

def _build_features_and_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Add P1 features and a forward-return label.

    Label: 1 if close_t+1 > close_t  (next-bar up move), else 0.
    Drops rows with NaN features or label.
    """
    # Import build_feature_set from this package
    training_dir = pathlib.Path(__file__).parent
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))

    try:
        from features import build_feature_set  # noqa: PLC0415
        df = build_feature_set(df)
    except ImportError:
        warnings.warn("training/features.py not found; using raw OHLCV columns only", stacklevel=2)
        _log.warning("training/features.py not found; using raw OHLCV columns only")

    # Simple binary label: did price go up on the next bar?
    df = df.copy()
    df["_label"] = (df["close"].shift(-1) > df["close"]).astype(float)

    # Drop the last row (no label) and any NaNs
    df.dropna(inplace=True)

    feature_cols = [
        c for c in df.columns
        if c not in ("open", "high", "low", "close", "volume", "time", "_label")
        and df[c].dtype in (np.float64, np.float32, float)
    ]

    X = df[feature_cols].copy()
    y = df["_label"].copy()
    return X, y


def _walk_forward_cv(
    X: pd.DataFrame,
    y: pd.Series,
    n_folds: int,
) -> dict:
    """
    Run expanding-window walk-forward CV with LogisticRegression.
    Returns dict with mean_auc, mean_brier, fold_aucs.
    """
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.metrics import roc_auc_score, brier_score_loss  # noqa: PLC0415
    from sklearn.preprocessing import StandardScaler  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415

    training_dir = pathlib.Path(__file__).parent
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))

    try:
        from cv import ExpandingWindowCV  # noqa: PLC0415
        splitter = ExpandingWindowCV(n_splits=n_folds)
    except ImportError:
        # Simple manual fallback
        warnings.warn("training/cv.py not found; using manual expanding split", stacklevel=2)
        _log.warning("training/cv.py not found; using manual expanding split")
        splitter = None

    Xn = X.to_numpy(dtype=float)
    yn = y.to_numpy(dtype=float)
    n = len(Xn)

    if splitter is None:
        fold_size = n // (n_folds + 1)
        splits = []
        for k in range(1, n_folds + 1):
            train_end = k * fold_size
            test_end = min((k + 1) * fold_size, n)
            if test_end > train_end:
                splits.append((np.arange(train_end), np.arange(train_end, test_end)))
    else:
        splits = list(splitter.split(Xn))

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=500, C=0.1, random_state=42)),
    ])

    fold_aucs: list[float] = []
    fold_briers: list[float] = []

    for train_idx, test_idx in splits:
        if len(train_idx) < 50 or len(test_idx) < 10:
            continue
        X_tr, X_te = Xn[train_idx], Xn[test_idx]
        y_tr, y_te = yn[train_idx], yn[test_idx]
        model.fit(X_tr, y_tr)
        proba = model.predict_proba(X_te)[:, 1]
        if len(np.unique(y_te)) < 2:
            continue
        fold_aucs.append(float(roc_auc_score(y_te, proba)))
        fold_briers.append(float(brier_score_loss(y_te, proba)))

    if not fold_aucs:
        return {"mean_auc": 0.0, "mean_brier": 1.0, "fold_aucs": [], "fold_briers": []}

    # Refit on full dataset for the final model
    model.fit(Xn, yn)

    return {
        "mean_auc": float(np.mean(fold_aucs)),
        "mean_brier": float(np.mean(fold_briers)),
        "fold_aucs": fold_aucs,
        "fold_briers": fold_briers,
        "fitted_model": model,
    }


def _export_onnx(model: Any, n_features: int, output_path: pathlib.Path) -> bool:
    """
    Export a fitted sklearn Pipeline to ONNX.  Returns True on success.
    """
    try:
        from skl2onnx import convert_sklearn  # noqa: PLC0415
        from skl2onnx.common.data_types import FloatTensorType  # noqa: PLC0415
        import onnx  # noqa: PLC0415

        initial_type = [("float_input", FloatTensorType([None, n_features]))]
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        output_path.write_bytes(onnx_model.SerializeToString())
        return True
    except Exception as exc:
        warnings.warn(f"ONNX export failed: {exc}; model not saved as ONNX", stacklevel=2)
        _log.warning("ONNX export failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_retrain(cfg: RetrainConfig) -> dict:
    """
    Execute a full retraining cycle.

    Steps:
        1. Fetch bars from backend
        2. Build P1 features + binary labels
        3. Quality gate (validate_bars)
        4. Walk-forward CV training
        5. Advanced gate evaluation
        6. Load current model metrics
        7. Optionally promote new model
        8. Write retrain_report.json

    Returns
    -------
    dict with keys:
        status         : str  — "success" | "failed" | "skipped"
        reason         : str  — short description of outcome
        new_model_path : str | None  — path to new ONNX model if exported
        metrics        : dict — CV metrics for the new model
        promoted       : bool — whether the new model replaced the old one
        report_path    : str  — path to retrain_report.json
    """
    started_at = datetime.now(tz=timezone.utc).isoformat()
    output_dir = pathlib.Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch bars
    df = _fetch_bars(cfg)
    if df.empty or len(df) < cfg.min_new_bars:
        return _write_report(output_dir, started_at, status="skipped",
                             reason=f"Insufficient bars: {len(df)} < {cfg.min_new_bars}",
                             metrics={}, promoted=False, new_model_path=None)

    # 2. Quality check
    training_dir = pathlib.Path(__file__).parent
    if str(training_dir) not in sys.path:
        sys.path.insert(0, str(training_dir))

    try:
        from quality import validate_bars  # noqa: PLC0415
        quality_result = validate_bars(df)
        if not quality_result.get("pass", True):
            return _write_report(output_dir, started_at, status="failed",
                                 reason=f"Quality gate failed: {quality_result}",
                                 metrics={}, promoted=False, new_model_path=None)
    except ImportError:
        quality_result = {"note": "quality.py not found; skipped quality check"}

    # 3. Build features + labels
    try:
        X, y = _build_features_and_labels(df)
    except Exception as exc:
        return _write_report(output_dir, started_at, status="failed",
                             reason=f"Feature engineering failed: {exc}",
                             metrics={}, promoted=False, new_model_path=None)

    if len(X) < cfg.min_new_bars:
        return _write_report(output_dir, started_at, status="skipped",
                             reason=f"Too few labelled bars after feature engineering: {len(X)}",
                             metrics={}, promoted=False, new_model_path=None)

    # 4. Walk-forward CV
    cv_result = _walk_forward_cv(X, y, n_folds=cfg.cv_folds)
    metrics = {
        "mean_auc": cv_result["mean_auc"],
        "mean_brier": cv_result["mean_brier"],
        "fold_aucs": cv_result.get("fold_aucs", []),
        "n_bars": len(X),
        "n_features": X.shape[1],
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "trained_at_utc": started_at,
    }

    # 5. Gate evaluation
    auc_pass = cv_result["mean_auc"] >= cfg.gate_auc_min
    brier_pass = cv_result["mean_brier"] <= cfg.gate_brier_max
    gates_pass = auc_pass and brier_pass

    metrics["gate_auc_pass"] = auc_pass
    metrics["gate_brier_pass"] = brier_pass
    metrics["gates_pass"] = gates_pass

    if not gates_pass:
        return _write_report(output_dir, started_at, status="failed",
                             reason=(
                                 f"Gates failed: AUC={cv_result['mean_auc']:.4f} "
                                 f"(min={cfg.gate_auc_min}), "
                                 f"Brier={cv_result['mean_brier']:.4f} "
                                 f"(max={cfg.gate_brier_max})"
                             ),
                             metrics=metrics, promoted=False, new_model_path=None)

    # 6. Compare vs current model
    current_metrics = load_current_metrics(cfg.output_dir)
    current_auc = current_metrics.get("mean_auc", 0.0)
    new_auc = cv_result["mean_auc"]
    better = new_auc > current_auc

    # 7. Export + promote
    promoted = False
    new_model_path: Optional[str] = None

    fitted_model = cv_result.get("fitted_model")
    if fitted_model is not None:
        candidate_path = output_dir / f"{cfg.model_name}_candidate.onnx"
        export_ok = _export_onnx(fitted_model, X.shape[1], candidate_path)
        if export_ok:
            new_model_path = str(candidate_path)

        if cfg.promote_if_better and better and export_ok:
            prod_path = output_dir / f"{cfg.model_name}.onnx"
            import shutil
            shutil.copy2(candidate_path, prod_path)
            promoted = True
            new_model_path = str(prod_path)

    # Write updated training_report.json if promoted
    if promoted:
        (output_dir / "training_report.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )

    reason = (
        f"New AUC={new_auc:.4f} vs current={current_auc:.4f}. "
        f"{'Promoted.' if promoted else 'Not promoted (not better or export failed).'}"
    )
    return _write_report(output_dir, started_at, status="success",
                         reason=reason, metrics=metrics,
                         promoted=promoted, new_model_path=new_model_path)


# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------

def _write_report(
    output_dir: pathlib.Path,
    started_at: str,
    status: str,
    reason: str,
    metrics: dict,
    promoted: bool,
    new_model_path: Optional[str],
) -> dict:
    report = {
        "status": status,
        "reason": reason,
        "new_model_path": new_model_path,
        "metrics": metrics,
        "promoted": promoted,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(tz=timezone.utc).isoformat(),
    }
    report_path = output_dir / "retrain_report.json"
    try:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError as exc:
        warnings.warn(f"Could not write retrain_report.json: {exc}", stacklevel=2)
        _log.warning("could not write retrain_report.json: %s", exc)
    report["report_path"] = str(report_path)
    return report
