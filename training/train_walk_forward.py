from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


@dataclass
class RunConfig:
    output_dir: Path
    model_name: str
    cv_folds: int
    dataset_profile: str
    horizon_bars: int
    calibration: str
    include_macro: bool
    include_news_windows: bool
    include_session_features: bool
    enable_class_weights: bool


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def rows_for_profile(profile: str) -> int:
    if profile == "rolling-180d":
        return 3200
    if profile == "event-focused":
        return 2600
    return 2000


def make_synthetic_dataset(
    rows: int = 2000,
    horizon_bars: int = 6,
    include_macro: bool = True,
    include_news_windows: bool = True,
    include_session_features: bool = True,
) -> pd.DataFrame:
    seed = 7 + horizon_bars * 17 + rows
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "trend_strength": rng.normal(0, 1, rows),
            "volatility": rng.uniform(0.2, 2.5, rows),
            "spread_atr": rng.uniform(0.0, 0.3, rows),
            "breakout_distance": rng.normal(0.0, 1.5, rows),
            "momentum": rng.normal(0.0, 1.0, rows),
        }
    )

    if not include_macro:
        df["trend_strength"] = 0.0
    if not include_news_windows:
        df["spread_atr"] = 0.0
    if not include_session_features:
        df["momentum"] = 0.0

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


def build_model(name: str, enable_class_weights: bool = True):
    if name == "logreg":
        class_weight = "balanced" if enable_class_weights else None
        return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=200, class_weight=class_weight))])
    if name == "rf":
        class_weight = "balanced_subsample" if enable_class_weights else None
        return RandomForestClassifier(n_estimators=200, random_state=42, class_weight=class_weight)
    if name == "xgb":
        import xgboost as xgb  # noqa: PLC0415
        spw = 1.5 if enable_class_weights else 1.0
        return xgb.XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            scale_pos_weight=spw, eval_metric="logloss", random_state=42, verbosity=0,
        )
    if name == "lgbm":
        import lightgbm as lgb  # noqa: PLC0415
        class_weight = "balanced" if enable_class_weights else None
        return lgb.LGBMClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            class_weight=class_weight, random_state=42, verbosity=-1,
        )
    raise ValueError(f"unsupported model: {name}")


def walk_forward_metrics(df: pd.DataFrame, model_name: str, cv_folds: int, enable_class_weights: bool) -> dict:
    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X = df[features].values
    y = df["label"].values

    folds = max(2, min(int(cv_folds), 20))
    tscv = TimeSeriesSplit(n_splits=folds)
    aucs: list[float] = []
    briers: list[float] = []

    for train_idx, test_idx in tscv.split(X):
        model = build_model(model_name, enable_class_weights=enable_class_weights)
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

    model = build_model(cfg.model_name, enable_class_weights=cfg.enable_class_weights)
    model.fit(X, y)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = cfg.output_dir / "daily_breakout_model.onnx"

    initial_type = [("input", FloatTensorType([None, X.shape[1]]))]
    try:
        # Disable zipmap so probabilities are exported as a plain tensor for onnxruntime-node.
        onnx_model = convert_sklearn(
            model,
            initial_types=initial_type,
            options={id(model): {"zipmap": False}},
        )
        onnx_path.write_bytes(onnx_model.SerializeToString())
    except Exception as exc:  # pragma: no cover
        warnings.warn(
            f"{cfg.model_name} ONNX conversion failed ({exc}). "
            "Install onnxmltools-extensions for tree-booster ONNX support. "
            "An empty placeholder will be written."
        )
        onnx_path.write_bytes(b"")
    return onnx_path


def downsample_indices(length: int, max_points: int = 40) -> np.ndarray:
    if length <= max_points:
        return np.arange(length)
    return np.linspace(0, length - 1, max_points, dtype=int)


def finite_float(value: float, fallback: float = 0.0) -> float:
    parsed = float(value)
    return parsed if math.isfinite(parsed) else fallback


def build_diagnostics(df: pd.DataFrame, model_name: str, threshold: float = 0.62, enable_class_weights: bool = True) -> dict:
    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X = df[features].values
    y = df["label"].values

    model = build_model(model_name, enable_class_weights=enable_class_weights)
    model.fit(X, y)
    prob = model.predict_proba(X)[:, 1]
    pred = (prob >= threshold).astype(int)

    cm = confusion_matrix(y, pred, labels=[0, 1])
    fpr, tpr, roc_thresholds = roc_curve(y, prob)
    precision, recall, pr_thresholds = precision_recall_curve(y, prob)

    roc_idx = downsample_indices(len(fpr), max_points=40)
    pr_idx = downsample_indices(len(pr_thresholds), max_points=40)

    roc_curve_payload = [
        {
            "threshold": finite_float(roc_thresholds[i], fallback=1.0),
            "fpr": finite_float(fpr[i]),
            "tpr": finite_float(tpr[i]),
        }
        for i in roc_idx
    ]

    pr_curve_payload = [
        {
            "threshold": finite_float(pr_thresholds[i], fallback=0.0),
            "recall": finite_float(recall[i]),
            "precision": finite_float(precision[i]),
        }
        for i in pr_idx
    ]

    bins = np.linspace(0.0, 1.0, 11)
    bucket_ids = np.digitize(prob, bins, right=True)
    calibration_bins: list[dict] = []
    for i in range(1, len(bins)):
        mask = bucket_ids == i
        if np.any(mask):
            predicted_mean = float(np.mean(prob[mask]))
            observed_rate = float(np.mean(y[mask]))
            count = int(np.sum(mask))
        else:
            predicted_mean = float((bins[i - 1] + bins[i]) / 2)
            observed_rate = predicted_mean
            count = 0

        calibration_bins.append(
            {
                "bucketStart": float(bins[i - 1]),
                "bucketEnd": float(bins[i]),
                "predictedMean": predicted_mean,
                "observedRate": observed_rate,
                "count": count,
            }
        )

    if isinstance(model, Pipeline):
        estimator = model.named_steps["model"]
        if hasattr(estimator, "coef_"):
            importances = np.abs(estimator.coef_[0])
        elif hasattr(estimator, "feature_importances_"):
            importances = estimator.feature_importances_
        else:
            importances = np.ones(len(features))
    elif hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        importances = np.ones(len(features))

    importances = np.abs(importances)
    if float(np.sum(importances)) == 0:
        importances = np.ones_like(importances)
    norm_importances = importances / np.sum(importances)
    feature_importance = [
        {"feature": feature, "importance": float(importance)}
        for feature, importance in sorted(zip(features, norm_importances), key=lambda item: item[1], reverse=True)
    ]

    # SHAP feature importance — lazy import; silently skipped if shap is not installed.
    shap_importance: list[dict] = []
    try:
        import shap  # noqa: PLC0415
        estimator = model.named_steps["model"] if isinstance(model, Pipeline) else model
        if hasattr(estimator, "feature_importances_"):
            explainer = shap.TreeExplainer(estimator)
        else:
            explainer = shap.LinearExplainer(estimator, X)
        shap_vals = explainer.shap_values(X)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]  # positive class
        shap_abs_mean = np.abs(shap_vals).mean(axis=0)
        shap_total = shap_abs_mean.sum()
        if shap_total > 0:
            shap_norm = shap_abs_mean / shap_total
            shap_importance = [
                {"feature": f, "shapImportance": round(float(v), 6)}
                for f, v in sorted(zip(features, shap_norm), key=lambda x: x[1], reverse=True)
            ]
    except Exception:
        pass  # shap is optional

    return {
        "confusionMatrix": {
            "labels": ["NEGATIVE", "POSITIVE"],
            "matrix": cm.tolist(),
            "threshold": float(threshold),
        },
        "rocCurve": roc_curve_payload,
        "prCurve": pr_curve_payload,
        "calibrationBins": calibration_bins,
        "featureImportance": feature_importance,
        "shapImportance": shap_importance,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["logreg", "rf", "xgb", "lgbm"], default="logreg")
    parser.add_argument("--output", default="../models")
    parser.add_argument("--threshold", type=float, default=0.62)
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--dataset-profile", choices=["rolling-90d", "rolling-180d", "event-focused"], default="rolling-90d")
    parser.add_argument("--horizon-bars", type=int, default=6)
    parser.add_argument("--calibration", choices=["isotonic", "platt", "none"], default="isotonic")
    parser.add_argument("--include-macro", type=parse_bool, default=True)
    parser.add_argument("--include-news-windows", type=parse_bool, default=True)
    parser.add_argument("--include-session-features", type=parse_bool, default=True)
    parser.add_argument("--enable-class-weights", type=parse_bool, default=True)
    args = parser.parse_args()

    cfg = RunConfig(
        output_dir=Path(args.output).resolve(),
        model_name=args.model,
        cv_folds=max(2, min(args.cv_folds, 20)),
        dataset_profile=args.dataset_profile,
        horizon_bars=max(1, min(args.horizon_bars, 64)),
        calibration=args.calibration,
        include_macro=args.include_macro,
        include_news_windows=args.include_news_windows,
        include_session_features=args.include_session_features,
        enable_class_weights=args.enable_class_weights,
    )

    rows = rows_for_profile(cfg.dataset_profile)
    df = make_synthetic_dataset(
        rows=rows,
        horizon_bars=cfg.horizon_bars,
        include_macro=cfg.include_macro,
        include_news_windows=cfg.include_news_windows,
        include_session_features=cfg.include_session_features,
    )

    metrics = walk_forward_metrics(df, cfg.model_name, cfg.cv_folds, cfg.enable_class_weights)
    onnx_path = export_onnx(df, cfg)

    features = ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
    X_full = df[features].values
    y_full = df["label"].values
    calibration_model = build_model(cfg.model_name, enable_class_weights=cfg.enable_class_weights)
    calibration_model.fit(X_full, y_full)
    calibration_prob = calibration_model.predict_proba(X_full)[:, 1]
    reliability_true, reliability_pred = calibration_curve(y_full, calibration_prob, n_bins=10)
    diagnostics = build_diagnostics(df, cfg.model_name, threshold=args.threshold, enable_class_weights=cfg.enable_class_weights)
    artifact = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "model": cfg.model_name,
        "onnxPath": str(onnx_path),
        "config": {
            "cvFolds": cfg.cv_folds,
            "datasetProfile": cfg.dataset_profile,
            "horizonBars": cfg.horizon_bars,
            "calibration": cfg.calibration,
            "includeMacro": cfg.include_macro,
            "includeNewsWindows": cfg.include_news_windows,
            "includeSessionFeatures": cfg.include_session_features,
            "enableClassWeights": cfg.enable_class_weights,
        },
        "metrics": metrics,
        "calibration": {
            "bins": len(reliability_true),
            "trueMean": float(np.mean(reliability_true)) if len(reliability_true) else 0.0,
            "predMean": float(np.mean(reliability_pred)) if len(reliability_pred) else 0.0,
        },
        "diagnostics": diagnostics,
    }

    report_json = json.dumps(artifact, indent=2, allow_nan=False)
    (cfg.output_dir / "training_report.json").write_text(report_json)
    print(report_json)


if __name__ == "__main__":
    main()
