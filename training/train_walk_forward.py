from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


@dataclass
class RunConfig:
    output_dir: Path
    model_name: str


def make_synthetic_dataset(rows: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "trend_strength": rng.normal(0, 1, rows),
            "volatility": rng.uniform(0.2, 2.5, rows),
            "spread_atr": rng.uniform(0.0, 0.3, rows),
            "breakout_distance": rng.normal(0.0, 1.5, rows),
            "momentum": rng.normal(0.0, 1.0, rows),
        }
    )
    score = (
        0.6 * df["trend_strength"]
        - 0.8 * df["spread_atr"]
        + 0.5 * df["breakout_distance"]
        + 0.4 * df["momentum"]
        - 0.3 * df["volatility"]
    )
    probs = 1 / (1 + np.exp(-score))
    df["label"] = (rng.uniform(0, 1, rows) < probs).astype(int)
    return df


def build_model(name: str):
    if name == "logreg":
        return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=200))])
    if name == "rf":
        return RandomForestClassifier(n_estimators=200, random_state=42)
    raise ValueError(f"unsupported model: {name}")


def walk_forward_metrics(df: pd.DataFrame, model_name: str) -> dict:
    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X = df[features].values
    y = df["label"].values

    tscv = TimeSeriesSplit(n_splits=5)
    aucs: list[float] = []
    briers: list[float] = []

    for train_idx, test_idx in tscv.split(X):
        model = build_model(model_name)
        model.fit(X[train_idx], y[train_idx])
        prob = model.predict_proba(X[test_idx])[:, 1]
        aucs.append(float(roc_auc_score(y[test_idx], prob)))
        briers.append(float(brier_score_loss(y[test_idx], prob)))

    return {
        "auc_mean": float(np.mean(aucs)),
        "auc_min": float(np.min(aucs)),
        "brier_mean": float(np.mean(briers)),
        "brier_max": float(np.max(briers)),
    }


def export_onnx(df: pd.DataFrame, cfg: RunConfig) -> Path:
    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X = df[features].values.astype(np.float32)
    y = df["label"].values

    model = build_model(cfg.model_name)
    model.fit(X, y)

    initial_type = [("input", FloatTensorType([None, X.shape[1]]))]
    # Disable zipmap so probabilities are exported as a plain tensor for onnxruntime-node.
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        options={id(model): {"zipmap": False}},
    )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = cfg.output_dir / "daily_breakout_model.onnx"
    onnx_path.write_bytes(onnx_model.SerializeToString())
    return onnx_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["logreg", "rf"], default="logreg")
    parser.add_argument("--output", default="../models")
    args = parser.parse_args()

    cfg = RunConfig(output_dir=Path(args.output).resolve(), model_name=args.model)
    df = make_synthetic_dataset()

    metrics = walk_forward_metrics(df, cfg.model_name)
    onnx_path = export_onnx(df, cfg)

    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X_full = df[features].values
    y_full = df["label"].values
    calibration_model = build_model(cfg.model_name)
    calibration_model.fit(X_full, y_full)
    calibration_prob = calibration_model.predict_proba(X_full)[:, 1]
    reliability_true, reliability_pred = calibration_curve(y_full, calibration_prob, n_bins=10)
    artifact = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "model": cfg.model_name,
        "onnxPath": str(onnx_path),
        "metrics": metrics,
        "calibration": {
            "bins": len(reliability_true),
            "trueMean": float(np.mean(reliability_true)) if len(reliability_true) else 0.0,
            "predMean": float(np.mean(reliability_pred)) if len(reliability_pred) else 0.0,
        },
    }

    (cfg.output_dir / "training_report.json").write_text(json.dumps(artifact, indent=2))
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
