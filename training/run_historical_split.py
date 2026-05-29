from __future__ import annotations

import argparse
import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, brier_score_loss, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from xgboost import XGBClassifier
from features import add_adx, add_efficiency_ratio, add_macd, add_rsi
from log_utils import setup_run_logger, write_event

_log = logging.getLogger("training.historical_split")


@dataclass
class Window:
    start: str
    end: str


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_bars(base_url: str, symbol: str, timeframe: str, source: str, window: Window, limit: int = 2000) -> pd.DataFrame:
    qs = urllib.parse.urlencode(
        {
            "source": source,
            "symbol": symbol,
            "timeframe": timeframe,
            "fromDate": window.start,
            "toDate": window.end,
            "limit": str(limit),
        }
    )
    payload = http_get_json(f"{base_url}/historical-data/bars?{qs}")
    items = payload.get("items", [])
    if not items:
        return pd.DataFrame(columns=["barCloseTimeUtc", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(items)
    df["barCloseTimeUtc"] = pd.to_datetime(df["barCloseTimeUtc"], utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["barCloseTimeUtc", "open", "high", "low", "close", "volume"]]


def chunk_days_for_timeframe(timeframe: str) -> int:
    # Keep each request comfortably below API max limit=2000 for deterministic full-range retrieval.
    if timeframe == "D1":
        return 1500
    if timeframe == "H4":
        return 300
    if timeframe == "H1":
        return 60
    if timeframe == "M15":
        return 10
    return 30


def fetch_bars_full_range(base_url: str, symbol: str, timeframe: str, source: str, window: Window) -> pd.DataFrame:
    start = datetime.strptime(window.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(window.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if start > end:
        return pd.DataFrame(columns=["barCloseTimeUtc", "open", "high", "low", "close", "volume"])

    step_days = chunk_days_for_timeframe(timeframe)
    chunks: list[pd.DataFrame] = []
    cur = start

    while cur <= end:
        chunk_end = min(cur + timedelta(days=step_days - 1), end)
        chunk_window = Window(cur.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d"))
        chunk_df = fetch_bars(base_url, symbol, timeframe, source, chunk_window, limit=2000)
        chunks.append(chunk_df)
        cur = chunk_end + timedelta(days=1)

    if not chunks:
        return pd.DataFrame(columns=["barCloseTimeUtc", "open", "high", "low", "close", "volume"])

    return (
        pd.concat(chunks, ignore_index=True)
        .drop_duplicates(subset=["barCloseTimeUtc"])
        .sort_values("barCloseTimeUtc")
        .reset_index(drop=True)
    )


_ANN_H4 = np.sqrt(252.0 * 6.0)  # H4 annualisation: 252 trading days × 6 bars/day


def compute_features(df: pd.DataFrame, horizon_bars: int) -> pd.DataFrame:
    """Compute all 16 TS-004 features plus forward return. Feature names match 04_feature_schema.md."""
    out = df.copy().sort_values("barCloseTimeUtc").reset_index(drop=True)

    # Log returns (5 features)
    out["ret1"] = np.log(out["close"] / out["close"].shift(1))
    out["ret2"] = np.log(out["close"] / out["close"].shift(2))
    out["ret3"] = np.log(out["close"] / out["close"].shift(3))
    out["ret5"] = np.log(out["close"] / out["close"].shift(5))
    out["ret10"] = np.log(out["close"] / out["close"].shift(10))

    # Volatility and regime ratio (3 features)
    out["volatility20"] = out["ret1"].rolling(20).std() * _ANN_H4
    out["volatility100"] = out["ret1"].rolling(100).std() * _ANN_H4
    out["volatility_regime"] = out["volatility20"] / out["volatility100"].replace(0.0, np.nan)

    # True range → ATR14 and ATR20
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [out["high"] - out["low"], (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr14 = tr.rolling(14).mean()
    atr20 = tr.rolling(20).mean()
    out["atr_normalised"] = atr14 / out["close"].replace(0.0, np.nan)  # 1 feature

    # SMA-based features (3 features)
    sma20 = out["close"].rolling(20).mean()
    sma200 = out["close"].rolling(200).mean()
    out["above_sma"] = (out["close"] > sma200).astype(int)
    out["trend_strength"] = (out["close"] - sma20) / atr20.replace(0.0, np.nan)
    high20 = out["high"].rolling(20).max()
    out["breakout_distance"] = (out["close"] - high20) / atr20.replace(0.0, np.nan)

    # Indicator features from features.py (4 features: adx, efficiency_ratio, rsi14, macd_signal)
    out = add_adx(out)             # → adx, adx_plus_di, adx_minus_di
    out = add_efficiency_ratio(out)  # → efficiency_ratio
    out = add_rsi(out)             # → rsi
    out = add_macd(out)            # → macd_line, macd_signal, macd_hist
    out = out.rename(columns={"rsi": "rsi14"})

    # Forward log return and preliminary label (refined by apply_label_objective)
    out["future_ret_h"] = np.log(out["close"].shift(-horizon_bars) / out["close"])
    out["label"] = (out["future_ret_h"] > 0).astype(int)

    core_cols = [
        "ret1", "ret2", "ret3", "ret5", "ret10",
        "volatility20", "volatility100", "volatility_regime",
        "atr_normalised", "above_sma", "trend_strength",
        "breakout_distance", "efficiency_ratio", "adx",
        "rsi14", "macd_signal",
    ]
    return out.dropna(subset=core_cols + ["future_ret_h"]).copy()


def make_model(scale_pos_weight: float = 1.0) -> CalibratedClassifierCV:
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    )
    return CalibratedClassifierCV(xgb, method="isotonic", cv=5)


def apply_label_objective(feat: pd.DataFrame, label_mode: str, min_edge_bps: float) -> pd.DataFrame:
    out = feat.copy()
    if label_mode == "direction":
        out["label"] = (out["future_ret_h"] > 0).astype(int)
    elif label_mode == "edge":
        min_edge = float(min_edge_bps) / 10000.0
        out["label"] = (out["future_ret_h"] > min_edge).astype(int)
    else:
        raise RuntimeError(f"Unsupported label mode: {label_mode}")
    return out


def compute_strategy_backtest_metrics(
    future_returns: np.ndarray,
    signals: np.ndarray,
    total_cost_per_trade: float = 0.0,
) -> dict:
    trade_returns = future_returns[signals == 1].copy()

    if trade_returns.size > 0 and total_cost_per_trade > 0:
        trade_returns = trade_returns - total_cost_per_trade

    total_trades = int(trade_returns.shape[0])

    if total_trades == 0:
        return {
            "totalTrades": 0,
            "winRate": 0.0,
            "netReturnPct": 0.0,
            "profitFactor": 0.0,
            "maxDrawdownPct": 0.0,
            "sharpeApprox": 0.0,
            "avgTradeReturnPct": 0.0,
        }

    wins = trade_returns[trade_returns > 0]
    losses = trade_returns[trade_returns < 0]

    win_rate = float(np.mean(trade_returns > 0))
    net_return_pct = float(np.sum(trade_returns) * 100.0)

    gross_profit = float(np.sum(wins))
    gross_loss_abs = float(np.abs(np.sum(losses)))
    if gross_loss_abs <= 1e-12:
        profit_factor = 999.0
    else:
        profit_factor = float(gross_profit / gross_loss_abs)

    equity_curve = np.cumprod(1.0 + trade_returns)
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve / running_max) - 1.0
    max_drawdown_pct = float(np.min(drawdown) * 100.0)

    std = float(np.std(trade_returns, ddof=1)) if total_trades > 1 else 0.0
    if std <= 1e-12:
        sharpe_approx = 0.0
    else:
        sharpe_approx = float((np.mean(trade_returns) / std) * _ANN_H4)

    avg_trade_return_pct = float(np.mean(trade_returns) * 100.0)

    return {
        "totalTrades": total_trades,
        "winRate": win_rate,
        "netReturnPct": net_return_pct,
        "profitFactor": profit_factor,
        "maxDrawdownPct": max_drawdown_pct,
        "sharpeApprox": sharpe_approx,
        "avgTradeReturnPct": avg_trade_return_pct,
    }


def build_variant_signals(
    variant: str,
    probs: np.ndarray,
    feat_slice: pd.DataFrame,
    threshold: float,
    trend_min_strength: float,
    trend_min_breakout_distance: float,
    split_trend_strength: float,
    mr_max_breakout_distance: float,
    mr_max_ret10: float,
    mr_max_volatility_regime: float,
    mr_threshold_offset: float,
    regime_gate: np.ndarray | None,
) -> np.ndarray:
    base = probs >= threshold

    trend_strength = feat_slice["trend_strength"].to_numpy(dtype=np.float64)
    breakout_distance = feat_slice["breakout_distance"].to_numpy(dtype=np.float64)
    ret10 = feat_slice["ret10"].to_numpy(dtype=np.float64)
    volatility_regime = feat_slice["volatility_regime"].to_numpy(dtype=np.float64)

    if variant == "baseline":
        signals = base
    elif variant == "trend-follow":
        trend_filter = (trend_strength >= trend_min_strength) & (breakout_distance >= trend_min_breakout_distance)
        signals = base & trend_filter
    elif variant == "regime-split":
        trend_regime = trend_strength >= split_trend_strength
        trend_filter = (breakout_distance >= trend_min_breakout_distance) & (trend_strength >= trend_min_strength)
        mr_threshold = max(0.01, min(0.99, threshold + mr_threshold_offset))
        mr_base = probs >= mr_threshold
        mr_filter = (
            (~trend_regime)
            & (breakout_distance <= mr_max_breakout_distance)
            & (ret10 <= mr_max_ret10)
            & (volatility_regime <= mr_max_volatility_regime)
        )
        signals = (trend_regime & base & trend_filter) | (mr_base & mr_filter)
    else:
        raise RuntimeError(f"Unsupported signal variant: {variant}")

    signal_int = signals.astype(np.int32)
    if regime_gate is not None:
        signal_int = (signal_int * regime_gate).astype(np.int32)
    return signal_int


def walk_forward_threshold_selection(
    train_feat: pd.DataFrame,
    feature_cols: list[str],
    thresholds: list[float],
    n_splits: int,
    embargo_bars: int,
    total_cost_per_trade: float,
    target_max_drawdown_pct: float | None,
    target_min_median_trades: float | None,
    fallback_min_median_trades: float,
    regime_gate_train: np.ndarray | None,
    signal_variant: str,
    trend_min_strength: float,
    trend_min_breakout_distance: float,
    split_trend_strength: float,
    mr_max_breakout_distance: float,
    mr_max_ret10: float,
    mr_max_volatility_regime: float,
    mr_threshold_offset: float,
    scale_pos_weight: float = 1.0,
) -> tuple[float, dict]:
    X = train_feat[feature_cols].to_numpy(dtype=np.float32)
    y = train_feat["label"].to_numpy(dtype=np.int32)
    future_returns = train_feat["future_ret_h"].to_numpy(dtype=np.float64)

    splitter = TimeSeriesSplit(n_splits=n_splits)
    threshold_stats = {thr: {"net": [], "pf": [], "dd": [], "trades": []} for thr in thresholds}
    fold_summaries: list[dict] = []

    for fold_id, (train_idx, val_idx) in enumerate(splitter.split(X), start=1):
        val_start = int(val_idx[0])
        cutoff = val_start - embargo_bars
        train_idx_eff = train_idx[train_idx < cutoff]

        if len(train_idx_eff) < 300 or len(val_idx) < 100:
            _log.debug("fold %d skipped: train=%d val=%d (below minimum)", fold_id, len(train_idx_eff), len(val_idx))
            continue

        _log.info("fold %d/%d  train=%d  val=%d  embargo=%d", fold_id, n_splits, len(train_idx_eff), len(val_idx), embargo_bars)
        model = make_model()
        model.fit(X[train_idx_eff], y[train_idx_eff])
        val_prob = model.predict_proba(X[val_idx])[:, 1]

        fold_row = {
            "fold": fold_id,
            "trainRows": int(len(train_idx_eff)),
            "validationRows": int(len(val_idx)),
            "embargoBars": int(embargo_bars),
            "thresholdMetrics": {},
        }

        for thr in thresholds:
            gate_slice = regime_gate_train[val_idx] if regime_gate_train is not None else None
            val_pred = build_variant_signals(
                variant=signal_variant,
                probs=val_prob,
                feat_slice=train_feat.iloc[val_idx],
                threshold=float(thr),
                trend_min_strength=trend_min_strength,
                trend_min_breakout_distance=trend_min_breakout_distance,
                split_trend_strength=split_trend_strength,
                mr_max_breakout_distance=mr_max_breakout_distance,
                mr_max_ret10=mr_max_ret10,
                mr_max_volatility_regime=mr_max_volatility_regime,
                mr_threshold_offset=mr_threshold_offset,
                regime_gate=gate_slice,
            )
            m = compute_strategy_backtest_metrics(
                future_returns[val_idx],
                val_pred,
                total_cost_per_trade=total_cost_per_trade,
            )
            threshold_stats[thr]["net"].append(m["netReturnPct"])
            threshold_stats[thr]["pf"].append(m["profitFactor"])
            threshold_stats[thr]["dd"].append(m["maxDrawdownPct"])
            threshold_stats[thr]["trades"].append(m["totalTrades"])
            fold_row["thresholdMetrics"][f"{thr:.2f}"] = m

        fold_summaries.append(fold_row)

    diagnostics: list[dict] = []
    for thr in thresholds:
        nets = threshold_stats[thr]["net"]
        pfs = threshold_stats[thr]["pf"]
        dds = threshold_stats[thr]["dd"]
        trades = threshold_stats[thr]["trades"]
        if len(nets) == 0:
            continue
        diagnostics.append(
            {
                "threshold": float(thr),
                "foldCount": int(len(nets)),
                "medianNetReturnPct": float(np.median(nets)),
                "medianProfitFactor": float(np.median(pfs)),
                "medianMaxDrawdownPct": float(np.median(dds)),
                "medianTrades": float(np.median(trades)),
            }
        )

    if not diagnostics:
        raise RuntimeError("Walk-forward threshold selection produced no valid folds")

    feasible = diagnostics
    feasibility_rules: dict[str, float] = {}

    if target_max_drawdown_pct is not None:
        feasibility_rules["targetMaxDrawdownPct"] = float(target_max_drawdown_pct)
        feasible = [row for row in feasible if row["medianMaxDrawdownPct"] >= target_max_drawdown_pct]

    if target_min_median_trades is not None:
        feasibility_rules["targetMinMedianTrades"] = float(target_min_median_trades)
        feasible = [row for row in feasible if row["medianTrades"] >= target_min_median_trades]

    if feasible:
        candidate_pool = feasible
        selection_mode = "constrained"
    else:
        # If constraints are infeasible, prevent zero-trade threshold selection.
        candidate_pool = [row for row in diagnostics if row["medianTrades"] >= fallback_min_median_trades]
        if not candidate_pool:
            raise RuntimeError(
                "No fallback threshold satisfies minimum median trade requirement "
                f"({fallback_min_median_trades})."
            )
        selection_mode = "fallback-risk-first"

    best = sorted(
        candidate_pool,
        key=lambda row: (
            row["medianMaxDrawdownPct"],
            row["medianProfitFactor"],
            row["medianNetReturnPct"],
        ),
        reverse=True,
    )[0]

    selection_report = {
        "foldsUsed": int(len(fold_summaries)),
        "thresholdDiagnostics": diagnostics,
        "selectedThreshold": float(best["threshold"]),
        "selectionMode": selection_mode,
        "constraintsSatisfied": bool(len(feasible) > 0),
        "feasibilityRules": feasibility_rules,
        "fallbackMinMedianTrades": float(fallback_min_median_trades),
        "foldSummaries": fold_summaries,
    }
    _log.info(
        "threshold selected: %.2f  mode=%s  folds=%d",
        float(best["threshold"]),
        selection_mode,
        int(len(fold_summaries)),
    )
    return float(best["threshold"]), selection_report


def export_onnx(model: CalibratedClassifierCV, feature_count: int, output_path: Path) -> None:
    initial_type = [("input", FloatTensorType([None, feature_count]))]
    onnx_model = convert_sklearn(model, initial_types=initial_type, options={id(model): {"zipmap": False}})
    output_path.write_bytes(onnx_model.SerializeToString())


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", choices=["D1", "H4", "H1", "M15"], default="D1")
    parser.add_argument("--source", default="FMP")
    parser.add_argument("--train-start", default="2014-05-27")
    parser.add_argument("--train-end", default="2024-05-27")
    parser.add_argument("--test-start", default="2024-05-28")
    parser.add_argument("--test-end", default="2026-05-27")
    parser.add_argument("--horizon-bars", type=int, default=5)
    parser.add_argument("--walk-forward-folds", type=int, default=5)
    parser.add_argument("--embargo-bars", type=int, default=5)
    parser.add_argument("--spread-bps", type=float, default=2.0)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--commission-bps", type=float, default=0.5)
    parser.add_argument("--stress-cost-multiplier", type=float, default=2.0)
    parser.add_argument("--threshold-grid", default="0.45,0.50,0.55,0.60")
    parser.add_argument("--target-max-drawdown-pct", type=float, default=None)
    parser.add_argument("--target-min-median-trades", type=float, default=None)
    parser.add_argument("--fallback-min-median-trades", type=float, default=1.0)
    parser.add_argument("--enable-regime-gate", action="store_true")
    parser.add_argument("--regime-min-volatility-regime", type=float, default=0.0)
    parser.add_argument("--regime-max-volatility-regime", type=float, default=2.0)
    parser.add_argument("--signal-variant", choices=["baseline", "trend-follow", "regime-split"], default="baseline")
    parser.add_argument("--trend-min-strength", type=float, default=0.0)
    parser.add_argument("--trend-min-breakout-distance", type=float, default=0.0)
    parser.add_argument("--split-trend-strength", type=float, default=0.0008)
    parser.add_argument("--mr-max-breakout-distance", type=float, default=-0.001)
    parser.add_argument("--mr-max-ret10", type=float, default=0.0)
    parser.add_argument("--mr-max-volatility-regime", type=float, default=1.3)
    parser.add_argument("--mr-threshold-offset", type=float, default=-0.05)
    parser.add_argument("--label-mode", choices=["direction", "edge"], default="direction")
    parser.add_argument("--min-edge-bps", type=float, default=5.0)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override auto-generated run directory. Defaults to logs/training/<date>/<time>_<symbol>_<timeframe>/",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional label appended to auto-generated run dir name, e.g. 'exp-001'",
    )
    args = parser.parse_args()

    logger, run_dir = setup_run_logger(
        symbol=args.symbol,
        timeframe=args.timeframe,
        label=args.run_label,
        output_dir=args.output_dir,
    )
    # Propagate to module-level logger so internal functions log to the same handlers.
    _log.handlers = logger.handlers
    _log.setLevel(logging.DEBUG)
    _log.propagate = False

    output_dir = run_dir  # kept for internal references

    run_config = {k: (list(v) if isinstance(v, list) else v) for k, v in vars(args).items()}
    run_config["generatedAtUtc"] = datetime.now(timezone.utc).isoformat()
    (run_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, default=str), encoding="utf-8")
    write_event(run_dir, "run_started", symbol=args.symbol, timeframe=args.timeframe, label=args.run_label)
    logger.info("run directory: %s", run_dir)
    logger.info(
        "config: symbol=%s timeframe=%s label-mode=%s min-edge-bps=%s horizon-bars=%d",
        args.symbol, args.timeframe, args.label_mode, args.min_edge_bps, args.horizon_bars,
    )

    thresholds = [float(item.strip()) for item in args.threshold_grid.split(",") if item.strip()]
    if not thresholds:
        raise RuntimeError("threshold grid cannot be empty")
    if any(thr <= 0.0 or thr >= 1.0 for thr in thresholds):
        raise RuntimeError("all thresholds must be strictly between 0 and 1")

    total_cost_per_trade = float(args.spread_bps + args.slippage_bps + args.commission_bps) / 10000.0
    stress_cost_per_trade = total_cost_per_trade * float(args.stress_cost_multiplier)

    # Ensure data exists in backend store for the full range.
    download_payload = {
        "source": args.source,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "fromDate": args.train_start,
        "toDate": args.test_end,
        "replaceExisting": False,
        "requestedBy": "historical-split-runner",
    }
    logger.info(
        "triggering data download: %s %s %s → %s",
        args.symbol, args.timeframe, args.train_start, args.test_end,
    )
    write_event(run_dir, "data_download_triggered",
                symbol=args.symbol, timeframe=args.timeframe,
                fromDate=args.train_start, toDate=args.test_end)
    download_result = http_post_json(f"{args.base_url}/historical-data/download", download_payload)
    logger.info("data download accepted")

    train_windows = [
        Window(args.train_start, "2017-12-31"),
        Window("2018-01-01", "2020-12-31"),
        Window("2021-01-01", args.train_end),
    ]
    logger.info("fetching train bars (%d windows)", len(train_windows))
    train_chunks = [fetch_bars_full_range(args.base_url, args.symbol, args.timeframe, args.source, w) for w in train_windows]
    train_df = pd.concat(train_chunks, ignore_index=True).drop_duplicates(subset=["barCloseTimeUtc"]).sort_values("barCloseTimeUtc")
    logger.info(
        "train bars: %d rows  range %s → %s",
        len(train_df),
        str(train_df["barCloseTimeUtc"].min())[:10] if len(train_df) else "—",
        str(train_df["barCloseTimeUtc"].max())[:10] if len(train_df) else "—",
    )

    logger.info("fetching test bars: %s → %s", args.test_start, args.test_end)
    test_df = fetch_bars_full_range(
        args.base_url,
        args.symbol,
        args.timeframe,
        args.source,
        Window(args.test_start, args.test_end),
    ).drop_duplicates(subset=["barCloseTimeUtc"]).sort_values("barCloseTimeUtc")
    logger.info("test bars: %d rows", len(test_df))
    write_event(run_dir, "bars_fetched", trainBars=len(train_df), testBars=len(test_df))

    if len(train_df) < 400:
        raise RuntimeError(f"Insufficient training bars fetched: {len(train_df)}")
    if len(test_df) < 100:
        raise RuntimeError(f"Insufficient test bars fetched: {len(test_df)}")

    logger.info("computing features  horizon=%d bars  label=%s  edge=%s bps", args.horizon_bars, args.label_mode, args.min_edge_bps)
    train_feat = compute_features(train_df, args.horizon_bars)
    test_feat = compute_features(test_df, args.horizon_bars)
    train_feat = apply_label_objective(train_feat, args.label_mode, float(args.min_edge_bps))
    test_feat = apply_label_objective(test_feat, args.label_mode, float(args.min_edge_bps))

    feature_cols = [
        "ret1", "ret2", "ret3", "ret5", "ret10",
        "volatility20", "volatility100", "volatility_regime",
        "atr_normalised", "above_sma", "trend_strength",
        "breakout_distance", "efficiency_ratio", "adx",
        "rsi14", "macd_signal",
    ]
    logger.info("feature rows: train=%d  test=%d  n_features=%d", len(train_feat), len(test_feat), len(feature_cols))
    write_event(run_dir, "features_computed", trainRows=len(train_feat), testRows=len(test_feat), nFeatures=len(feature_cols))
    (run_dir / "feature_schema.json").write_text(
        json.dumps({
            "version": "ts004_v1",
            "features": [{"name": c, "type": "float"} for c in feature_cols],
            "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
            "source_script": "training/run_historical_split.py",
        }, indent=2),
        encoding="utf-8",
    )

    regime_gate_train = None
    regime_gate_test = None
    if args.enable_regime_gate:
        regime_gate_train = (
            (train_feat["volatility_regime"] >= float(args.regime_min_volatility_regime))
            & (train_feat["volatility_regime"] <= float(args.regime_max_volatility_regime))
        ).to_numpy(dtype=np.int32)
        regime_gate_test = (
            (test_feat["volatility_regime"] >= float(args.regime_min_volatility_regime))
            & (test_feat["volatility_regime"] <= float(args.regime_max_volatility_regime))
        ).to_numpy(dtype=np.int32)

    X_train = train_feat[feature_cols].to_numpy(dtype=np.float32)
    y_train = train_feat["label"].to_numpy(dtype=np.int32)
    X_test = test_feat[feature_cols].to_numpy(dtype=np.float32)
    y_test = test_feat["label"].to_numpy(dtype=np.int32)

    neg_count = int(np.sum(y_train == 0))
    pos_count = int(np.sum(y_train == 1))
    scale_pos_weight = float(neg_count) / max(1, pos_count)

    logger.info(
        "walk-forward threshold selection: folds=%d  embargo=%d  thresholds=%s  variant=%s",
        args.walk_forward_folds, args.embargo_bars, thresholds, args.signal_variant,
    )
    write_event(run_dir, "walk_forward_started",
                folds=args.walk_forward_folds,
                embargo=args.embargo_bars,
                thresholds=thresholds,
                signalVariant=args.signal_variant)
    selected_threshold, wf_report = walk_forward_threshold_selection(
        train_feat,
        feature_cols,
        thresholds,
        n_splits=max(2, int(args.walk_forward_folds)),
        embargo_bars=max(0, int(args.embargo_bars)),
        total_cost_per_trade=total_cost_per_trade,
        target_max_drawdown_pct=args.target_max_drawdown_pct,
        target_min_median_trades=args.target_min_median_trades,
        fallback_min_median_trades=max(1.0, float(args.fallback_min_median_trades)),
        regime_gate_train=regime_gate_train,
        signal_variant=args.signal_variant,
        trend_min_strength=float(args.trend_min_strength),
        trend_min_breakout_distance=float(args.trend_min_breakout_distance),
        split_trend_strength=float(args.split_trend_strength),
        mr_max_breakout_distance=float(args.mr_max_breakout_distance),
        mr_max_ret10=float(args.mr_max_ret10),
        mr_max_volatility_regime=float(args.mr_max_volatility_regime),
        mr_threshold_offset=float(args.mr_threshold_offset),
        scale_pos_weight=scale_pos_weight,
    )

    logger.info(
        "threshold selected: %.2f (mode=%s)  training final model on %d rows  scale_pos_weight=%.3f",
        selected_threshold, wf_report.get("selectionMode", "?"), len(X_train), scale_pos_weight,
    )
    write_event(run_dir, "threshold_selected",
                threshold=selected_threshold,
                mode=wf_report.get("selectionMode"))
    model = make_model(scale_pos_weight=scale_pos_weight)
    model.fit(X_train, y_train)
    logger.info("final model trained")

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = build_variant_signals(
        variant=args.signal_variant,
        probs=y_prob,
        feat_slice=test_feat,
        threshold=float(selected_threshold),
        trend_min_strength=float(args.trend_min_strength),
        trend_min_breakout_distance=float(args.trend_min_breakout_distance),
        split_trend_strength=float(args.split_trend_strength),
        mr_max_breakout_distance=float(args.mr_max_breakout_distance),
        mr_max_ret10=float(args.mr_max_ret10),
        mr_max_volatility_regime=float(args.mr_max_volatility_regime),
        mr_threshold_offset=float(args.mr_threshold_offset),
        regime_gate=regime_gate_test,
    )

    metrics = {
        "auc": safe_auc(y_test, y_prob),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_test, y_prob)),
        "testPositiveRate": float(np.mean(y_test)),
        "predictedPositiveRate": float(np.mean(y_pred)),
        "selectedThreshold": float(selected_threshold),
    }

    strategy_metrics_no_cost = compute_strategy_backtest_metrics(
        test_feat["future_ret_h"].to_numpy(dtype=np.float64),
        y_pred,
        total_cost_per_trade=0.0,
    )

    strategy_metrics_base_cost = compute_strategy_backtest_metrics(
        test_feat["future_ret_h"].to_numpy(dtype=np.float64),
        y_pred,
        total_cost_per_trade=total_cost_per_trade,
    )

    strategy_metrics_stress_cost = compute_strategy_backtest_metrics(
        test_feat["future_ret_h"].to_numpy(dtype=np.float64),
        y_pred,
        total_cost_per_trade=stress_cost_per_trade,
    )

    model_path = run_dir / "model.onnx"
    logger.info("exporting ONNX model → %s", model_path.name)
    export_onnx(model, len(feature_cols), model_path)
    write_event(run_dir, "model_exported", path=str(model_path))
    logger.info("model exported")

    report = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "baseUrl": args.base_url,
        "source": args.source,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "trainWindow": {"start": args.train_start, "end": args.train_end},
        "testWindow": {"start": args.test_start, "end": args.test_end},
        "horizonBars": args.horizon_bars,
        "walkForwardFolds": int(args.walk_forward_folds),
        "embargoBars": int(args.embargo_bars),
        "costAssumptions": {
            "spreadBps": float(args.spread_bps),
            "slippageBps": float(args.slippage_bps),
            "commissionBps": float(args.commission_bps),
            "totalCostPerTrade": float(total_cost_per_trade),
            "stressCostMultiplier": float(args.stress_cost_multiplier),
            "stressCostPerTrade": float(stress_cost_per_trade),
        },
        "regimeGate": {
            "enabled": bool(args.enable_regime_gate),
            "minVolatilityRegime": float(args.regime_min_volatility_regime),
            "maxVolatilityRegime": float(args.regime_max_volatility_regime),
        },
        "signalVariant": {
            "name": args.signal_variant,
            "trendMinStrength": float(args.trend_min_strength),
            "trendMinBreakoutDistance": float(args.trend_min_breakout_distance),
            "splitTrendStrength": float(args.split_trend_strength),
            "mrMaxBreakoutDistance": float(args.mr_max_breakout_distance),
            "mrMaxRet10": float(args.mr_max_ret10),
            "mrMaxVolatilityRegime": float(args.mr_max_volatility_regime),
            "mrThresholdOffset": float(args.mr_threshold_offset),
        },
        "labelObjective": {
            "mode": args.label_mode,
            "minEdgeBps": float(args.min_edge_bps),
        },
        "walkForwardSelection": wf_report,
        "downloadJob": download_result.get("job", {}),
        "bars": {
            "trainFetched": int(len(train_df)),
            "testFetched": int(len(test_df)),
            "trainFeatureRows": int(len(train_feat)),
            "testFeatureRows": int(len(test_feat)),
        },
        "metrics": metrics,
        "strategyBacktest": strategy_metrics_base_cost,
        "strategyBacktestNoCost": strategy_metrics_no_cost,
        "strategyBacktestStressCost": strategy_metrics_stress_cost,
        "modelPath": str(model_path),
    }

    report_path = run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_event(
        run_dir,
        "run_complete",
        auc=metrics.get("auc"),
        profitFactor=strategy_metrics_base_cost.get("profitFactor"),
        maxDrawdownPct=strategy_metrics_base_cost.get("maxDrawdownPct"),
        totalTrades=strategy_metrics_base_cost.get("totalTrades"),
        selectedThreshold=float(selected_threshold),
        runDir=str(run_dir),
    )
    logger.info("report written → %s", report_path)
    logger.info(
        "RESULT  AUC=%.4f  PF=%.3f  maxDD=%.1f%%  trades=%d  threshold=%.2f",
        metrics.get("auc") or 0.0,
        strategy_metrics_base_cost.get("profitFactor", 0.0),
        abs(strategy_metrics_base_cost.get("maxDrawdownPct", 0.0)),
        strategy_metrics_base_cost.get("totalTrades", 0),
        selected_threshold,
    )
    logger.info("run dir: %s", run_dir)


if __name__ == "__main__":
    main()
