"""
Model performance monitoring alerts.

Detects when live model precision drifts below the training baseline
and writes a monitoring_alert.json file for the backend to consume.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def check_performance_drift(
    recent_predictions: list[dict],
    baseline_precision: float,
    alert_threshold: float = 0.05,
    signal_threshold: float = 0.62,
) -> dict:
    """
    Compare recent live precision against the training baseline.

    recent_predictions: list of {"label": int, "prob": float} from live signals.
    alert_threshold: absolute precision drop that triggers an alert.

    Returns a status dict with keys:
      status               "alert" | "ok" | "insufficient_data" | "no_signals"
      baseline_precision   float
      recent_precision     float  (omitted for insufficient_data / no_signals)
      drift                float  (positive = degradation)
      alert_threshold      float
      n_samples            int
      n_signals            int
      generated_at_utc     str (ISO-8601)
    """
    ts = datetime.now(timezone.utc).isoformat()

    if len(recent_predictions) < 10:
        return {
            "status": "insufficient_data",
            "baseline_precision": baseline_precision,
            "n_samples": len(recent_predictions),
            "generated_at_utc": ts,
        }

    labels = np.array([p["label"] for p in recent_predictions], dtype=int)
    probs = np.array([p["prob"] for p in recent_predictions], dtype=float)
    pred = (probs >= signal_threshold).astype(int)
    active = pred == 1

    if int(active.sum()) == 0:
        return {
            "status": "no_signals",
            "baseline_precision": baseline_precision,
            "n_samples": len(recent_predictions),
            "n_signals": 0,
            "generated_at_utc": ts,
        }

    recent_precision = float(np.mean(labels[active]))
    drift = baseline_precision - recent_precision

    return {
        "status": "alert" if drift > alert_threshold else "ok",
        "baseline_precision": round(baseline_precision, 4),
        "recent_precision": round(recent_precision, 4),
        "drift": round(drift, 4),
        "alert_threshold": alert_threshold,
        "n_samples": len(recent_predictions),
        "n_signals": int(active.sum()),
        "generated_at_utc": ts,
    }


def write_monitoring_alert(output_dir: Path, alert: dict) -> Path:
    """
    Write alert dict to <output_dir>/monitoring_alert.json.
    Creates the directory if needed and overwrites any existing file.
    Returns the path written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "monitoring_alert.json"
    out_path.write_text(json.dumps(alert, indent=2), encoding="utf-8")
    return out_path
