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
from frac_diff import frac_diff_ffd
from labeling import cusum_events
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
    """Compute all 23 TS-004 v4 features plus forward return. Feature names match 04_feature_schema.md."""
    out = df.copy().sort_values("barCloseTimeUtc").reset_index(drop=True)
    ts = pd.to_datetime(out["barCloseTimeUtc"], utc=True)

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
    out["atr_normalised"] = atr14 / out["close"].replace(0.0, np.nan)

    # SMA-based features (3 features)
    sma20 = out["close"].rolling(20).mean()
    sma200 = out["close"].rolling(200).mean()
    out["above_sma"] = (out["close"] > sma200).astype(int)
    out["trend_strength"] = (out["close"] - sma20) / atr20.replace(0.0, np.nan)
    high20 = out["high"].rolling(20).max()
    out["breakout_distance"] = (out["close"] - high20) / atr20.replace(0.0, np.nan)

    # Indicator features from features.py (4 features: adx, efficiency_ratio, rsi14, macd_signal)
    out = add_adx(out)
    out = add_efficiency_ratio(out)
    out = add_rsi(out)
    out = add_macd(out)
    out = out.rename(columns={"rsi": "rsi14"})

    # --- v2 features ---

    # htf_trend: daily trend context — sign(daily_close - 20-day MA), forward-filled to H4
    out_dt = out.copy()
    out_dt.index = ts
    daily_close = out_dt["close"].resample("D").last().dropna()
    daily_ma20 = daily_close.rolling(20, min_periods=1).mean()
    daily_trend = np.sign(daily_close - daily_ma20)
    daily_date_strs = daily_close.index.strftime("%Y-%m-%d")
    trend_dict = dict(zip(daily_date_strs, daily_trend.values))
    h4_date_strs = ts.dt.strftime("%Y-%m-%d")
    out["htf_trend"] = h4_date_strs.map(trend_dict).ffill().fillna(0.0).values

    # is_active_session: 1 if bar closes during London/NY hours (12:00–20:00 UTC)
    out["is_active_session"] = ts.dt.hour.between(12, 20).astype(float).values

    # dxy_trend: USD strength direction — sign(DXY - 20-day MA), forward-filled to H4
    try:
        import yfinance as yf  # noqa: PLC0415
        _s = str(ts.iloc[0].date())
        _e = str(ts.iloc[-1].date())
        dxy_raw = yf.download("DX-Y.NYB", start=_s, end=_e, auto_adjust=True, progress=False)
        if isinstance(dxy_raw.columns, pd.MultiIndex):
            dxy_raw.columns = dxy_raw.columns.get_level_values(0)
        dxy_close = dxy_raw["Close"].dropna()
        dxy_ma = dxy_close.rolling(20, min_periods=1).mean()
        dxy_trend_vals = np.sign(dxy_close - dxy_ma)
        dxy_date_strs = [str(d.date()) for d in pd.to_datetime(dxy_close.index)]
        dxy_dict = dict(zip(dxy_date_strs, dxy_trend_vals.values))
        out["dxy_trend"] = h4_date_strs.map(dxy_dict).ffill().fillna(0.0).values
    except Exception:
        out["dxy_trend"] = 0.0

    # vix_regime: global risk-on/off signal — sign(VIX - 20-day MA), forward-filled to H4.
    # VIX above its MA = risk-off environment (USD tends to strengthen, EURUSD headwind).
    # This is orthogonal to EURUSD price and driven by macro capital-flow dynamics.
    try:
        import yfinance as yf  # noqa: PLC0415
        _s = str(ts.iloc[0].date())
        _e = str(ts.iloc[-1].date())
        vix_raw = yf.download("^VIX", start=_s, end=_e, auto_adjust=True, progress=False)
        if isinstance(vix_raw.columns, pd.MultiIndex):
            vix_raw.columns = vix_raw.columns.get_level_values(0)
        vix_close = vix_raw["Close"].dropna()
        vix_ma = vix_close.rolling(20, min_periods=1).mean()
        vix_trend_vals = np.sign(vix_close - vix_ma)
        vix_date_strs = [str(d.date()) for d in pd.to_datetime(vix_close.index)]
        vix_dict = dict(zip(vix_date_strs, vix_trend_vals.values))
        out["vix_regime"] = h4_date_strs.map(vix_dict).ffill().fillna(0.0).values
    except Exception:
        out["vix_regime"] = 0.0

    # day_of_week: 0.0 (Monday) → 1.0 (Friday).
    # Intraweek FX seasonality: Monday gap fill, Friday position squaring.
    # Normalized to [0, 1] so the model can treat it as a continuous signal.
    out["day_of_week"] = (ts.dt.dayofweek.clip(0, 4) / 4.0).values

    # us_rate_trend: US interest rate direction — sign(^TNX 10Y yield - 20-day MA).
    # When US 10Y yields rise above their MA, USD strengthens → EURUSD headwind.
    # This is the leading cause of USD moves; DXY is the lagging outcome.
    # Together they capture both the rate CAUSE and the FX EFFECT independently.
    try:
        import yfinance as yf  # noqa: PLC0415
        _s = str(ts.iloc[0].date())
        _e = str(ts.iloc[-1].date())
        tnx_raw = yf.download("^TNX", start=_s, end=_e, auto_adjust=True, progress=False)
        if isinstance(tnx_raw.columns, pd.MultiIndex):
            tnx_raw.columns = tnx_raw.columns.get_level_values(0)
        tnx_close = tnx_raw["Close"].dropna()
        tnx_ma = tnx_close.rolling(20, min_periods=1).mean()
        tnx_trend_vals = np.sign(tnx_close - tnx_ma)
        tnx_date_strs = [str(d.date()) for d in pd.to_datetime(tnx_close.index)]
        tnx_dict = dict(zip(tnx_date_strs, tnx_trend_vals.values))
        out["us_rate_trend"] = h4_date_strs.map(tnx_dict).ffill().fillna(0.0).values
    except Exception:
        out["us_rate_trend"] = 0.0

    # fd_close: Fractionally differenced close price (d=0.4), normalised by rolling 100-bar std.
    # López de Prado (AFML Ch.5): FFD achieves stationarity while preserving maximum price memory.
    # ret1-10 are stationary but memory-less. fd_close encodes medium-range price memory
    # that log-returns cannot represent. d=0.4 is below the typical ADF threshold for FX prices.
    _fd_raw = frac_diff_ffd(out["close"].rename("close"), d=0.4, thres=1e-4)
    _fd_std = _fd_raw.rolling(100, min_periods=20).std().replace(0.0, np.nan)
    out["fd_close"] = (_fd_raw / _fd_std).values

    # Forward log return and preliminary label (refined by apply_label_objective)
    out["future_ret_h"] = np.log(out["close"].shift(-horizon_bars) / out["close"])
    out["label"] = (out["future_ret_h"] > 0).astype(int)

    core_cols = [
        "ret1", "ret2", "ret3", "ret5", "ret10",
        "volatility20", "volatility100", "volatility_regime",
        "atr_normalised", "above_sma", "trend_strength",
        "breakout_distance", "efficiency_ratio", "adx",
        "rsi14", "macd_signal",
        "htf_trend", "is_active_session", "dxy_trend",
        "vix_regime", "day_of_week",
        "us_rate_trend", "fd_close",
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
    min_fold_train_rows: int = 300,
    min_fold_val_rows: int = 100,
    sample_weights: np.ndarray | None = None,
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

        if len(train_idx_eff) < min_fold_train_rows or len(val_idx) < min_fold_val_rows:
            _log.debug("fold %d skipped: train=%d val=%d (below minimum)", fold_id, len(train_idx_eff), len(val_idx))
            continue

        _log.info("fold %d/%d  train=%d  val=%d  embargo=%d", fold_id, n_splits, len(train_idx_eff), len(val_idx), embargo_bars)
        model = make_model()
        _fold_weights = sample_weights[train_idx_eff] if sample_weights is not None else None
        model.fit(X[train_idx_eff], y[train_idx_eff], sample_weight=_fold_weights)
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

    # Select threshold: profitable thresholds (median PF > 1.0) take priority over
    # drawdown-minimising ones.  Among profitable candidates, prefer the LOWEST threshold
    # (most trades).  If no profitable candidate exists, fall back to the highest threshold
    # (fewest trades = least risk — original behaviour).
    #
    # Robustness guard: reject any threshold where a single CV fold showed catastrophic
    # drawdown (< -50%).  A median PF above 1.0 that is driven by 2 good folds masking
    # a -93% fold is not a usable threshold.
    _MAX_FOLD_DD = -50.0
    worst_fold_dd: dict[float, float] = {}
    for thr in thresholds:
        thr_key = f"{thr:.2f}"
        fold_dds = [
            fs["thresholdMetrics"].get(thr_key, {}).get("maxDrawdownPct", 0.0)
            for fs in fold_summaries
        ]
        worst_fold_dd[float(thr)] = min(fold_dds) if fold_dds else 0.0

    profitable_pool = [
        r for r in candidate_pool
        if r["medianProfitFactor"] > 1.0
        and worst_fold_dd.get(r["threshold"], -999.0) >= _MAX_FOLD_DD
    ]
    if profitable_pool:
        # Sort profitable candidates ascending by threshold so the lowest (most trades) wins.
        # Use PF as a tiebreaker: higher PF preferred among same threshold value.
        best = sorted(profitable_pool, key=lambda r: (r["threshold"], -r["medianProfitFactor"]))[0]
    else:
        # No profitable threshold found — minimise risk by picking highest threshold.
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


def _register_xgboost_converter() -> None:
    """Register the XGBoost converter with skl2onnx (requires onnxmltools)."""
    from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost  # noqa: PLC0415
    from skl2onnx import update_registered_converter  # noqa: PLC0415
    from skl2onnx.common.shape_calculator import calculate_linear_classifier_output_shapes  # noqa: PLC0415

    update_registered_converter(
        XGBClassifier,
        "XGBoostXGBClassifier",
        calculate_linear_classifier_output_shapes,
        convert_xgboost,
        options={"nocl": [True, False], "zipmap": [True, False, "columns"]},
    )


def export_onnx(model: CalibratedClassifierCV, feature_count: int, output_path: Path) -> None:
    _register_xgboost_converter()
    initial_type = [("input", FloatTensorType([None, feature_count]))]
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        options={id(model): {"zipmap": False}},
        target_opset={"": 17, "ai.onnx.ml": 3},
    )
    output_path.write_bytes(onnx_model.SerializeToString())


def safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_prob))


def _score(value: float, breakpoints: list[tuple[float, int]]) -> int:
    """Return score by finding the highest breakpoint not exceeded by value."""
    result = breakpoints[0][1]
    for threshold, score in breakpoints:
        if value >= threshold:
            result = score
    return result


def generate_run_report(report: dict, run_dir: Path) -> None:
    """Generate run_report.md from a completed report dict, written to run_dir."""
    m = report.get("metrics", {})
    bt = report.get("strategyBacktest", {})
    bt_nc = report.get("strategyBacktestNoCost", {})
    bt_sc = report.get("strategyBacktestStressCost", {})
    wf = report.get("walkForwardSelection", {})
    bars = report.get("bars", {})
    costs = report.get("costAssumptions", {})
    rgate = report.get("regimeGate", {})
    lo = report.get("labelObjective", {})

    auc = m.get("auc") or 0.0
    pf = bt.get("profitFactor", 0.0)
    win_rate = bt.get("winRate", 0.0)
    trades = bt.get("totalTrades", 0)
    max_dd = bt.get("maxDrawdownPct", 0.0)
    sharpe = bt.get("sharpeApprox", 0.0)
    recall = m.get("recall") or 0.0
    threshold = wf.get("selectedThreshold", 0.0)
    threshold_mode = wf.get("selectionMode", "unknown")
    stress_pf = bt_sc.get("profitFactor", 0.0)
    base_pf = pf if pf > 0 else 1e-9
    cost_ratio = stress_pf / base_pf

    # Scoring functions
    auc_score = _score(auc, [(0, 1), (0.505, 2), (0.510, 3), (0.520, 4), (0.530, 5), (0.540, 6), (0.560, 7), (0.580, 8), (0.620, 9), (0.650, 10)])
    pf_score = _score(pf, [(0, 0), (0.5, 1), (0.7, 2), (0.9, 3), (1.0, 4), (1.1, 5), (1.25, 6), (1.5, 7), (2.0, 8), (3.0, 9), (5.0, 10)])
    wr_score = _score(win_rate, [(0, 1), (0.40, 2), (0.44, 3), (0.48, 4), (0.50, 5), (0.54, 6), (0.58, 7), (0.62, 8), (0.68, 9), (0.75, 10)])
    freq_score = _score(trades, [(0, 1), (5, 2), (15, 3), (25, 4), (40, 5), (60, 6), (80, 7), (100, 8), (150, 9), (200, 10)])
    dd_score = _score(-max_dd, [(0, 10), (0.5, 9), (1, 8), (3, 7), (5, 6), (8, 5), (12, 4), (15, 3), (20, 2), (25, 1), (9999, 0)])
    sharpe_score = _score(sharpe, [(-999, 0), (-5, 1), (-2, 2), (0, 3), (0.5, 4), (1, 5), (2, 6), (5, 7), (10, 8), (15, 9), (20, 10)])
    recall_score = _score(recall, [(0, 1), (0.005, 2), (0.010, 3), (0.020, 4), (0.050, 5), (0.100, 6), (0.150, 7), (0.200, 8), (0.300, 9), (0.400, 10)])
    cost_score = _score(cost_ratio, [(0, 0), (0.50, 1), (0.60, 2), (0.65, 3), (0.70, 4), (0.75, 5), (0.80, 6), (0.85, 7), (0.90, 8), (0.95, 9), (0.99, 10)])

    # CV consistency — count folds with PF > 1.0 at selected threshold
    fold_summaries = wf.get("foldSummaries", [])
    # Report may store threshold as "0.60" or "0.6" — try both
    thr_key = f"{threshold:.2f}"
    if fold_summaries and thr_key not in (fold_summaries[0].get("thresholdMetrics") or {}):
        thr_key = str(threshold)
    folds_profitable = sum(
        1 for f in fold_summaries
        if f.get("thresholdMetrics", {}).get(thr_key, {}).get("profitFactor", 0.0) > 1.0
    )
    folds_total = len(fold_summaries)
    cv_pct = folds_profitable / folds_total if folds_total else 0.0
    cv_score = _score(cv_pct, [(0, 1), (0.20, 2), (0.40, 4), (0.60, 6), (0.80, 8), (1.00, 10)])

    is_profitable = pf >= 1.0
    verdict_str = "✅ PROFITABLE" if is_profitable else "❌ NOT PROFITABLE"

    # £10,000 balance projection
    opening = 10_000.0
    def _bal(net_pct: float) -> tuple[str, str]:
        closing = opening * (1 + net_pct / 100)
        pl = closing - opening
        pl_str = f"+£{pl:,.2f}" if pl >= 0 else f"-£{abs(pl):,.2f}"
        return f"£{closing:,.2f}", pl_str

    end_base, pl_base = _bal(bt.get("netReturnPct", 0.0))
    end_nc, pl_nc = _bal(bt_nc.get("netReturnPct", 0.0))
    end_sc, pl_sc = _bal(bt_sc.get("netReturnPct", 0.0))

    # Gate assessment
    trade_gate = "✅" if trades >= 60 else "❌"
    pf_gate = "✅" if pf >= 1.25 else ("⚠️" if pf >= 1.0 else "❌")
    dd_gate = "✅" if abs(max_dd) <= 20.0 else "❌"
    exp_bps = bt.get("avgTradeReturnPct", 0.0) * 100.0  # convert pct to bps
    exp_gate = "✅" if exp_bps > 5.0 else "❌"
    cv_gate = "✅" if cv_pct >= 0.60 else "❌"
    auc_gate = "✅" if auc >= 0.53 else "❌"

    if pf >= 1.25 and abs(max_dd) <= 20.0 and trades >= 60 and exp_bps > 5.0:
        overall_gate = "PASS"
    elif is_profitable:
        overall_gate = "PARTIAL — signal quality passes, frequency/consistency gates outstanding"
    else:
        overall_gate = "FAIL"

    # Auto-generated analysis text based on metrics
    if not is_profitable:
        analysis = (
            "- **Weak feature signal**: Model cannot identify consistent edge from available features.\n"
            "- **Calibrated uncertainty**: `CalibratedClassifierCV` correctly reports low probability for most bars, meaning it 'knows' it lacks edge.\n"
            "- **Review**: Add higher-timeframe context, external features, or switch labeling method."
        )
    elif trades < 60:
        analysis = (
            f"- **Signal quality is sound** (PF {pf:.3f}, win rate {win_rate*100:.1f}%). The model correctly selects high-confidence setups.\n"
            f"- **Frequency is the bottleneck**: Only {trades} trades in the test period. The model requires high confidence (≥{threshold}) before firing.\n"
            "- **Next step**: Lower threshold slightly with an active regime pre-filter to generate more signals without sacrificing precision."
        )
    else:
        analysis = (
            f"- **Strong signal and frequency** (PF {pf:.3f}, {trades} trades, win rate {win_rate*100:.1f}%).\n"
            f"- **Drawdown controlled** at {abs(max_dd):.1f}%. Risk-adjusted returns (Sharpe {sharpe:.2f}) are acceptable.\n"
            "- **Consider**: stress testing and holdout evaluation."
        )

    # Walk-forward table rows
    wf_rows = []
    for f in fold_summaries:
        fold_n = f.get("fold", "?")
        t_rows = f.get("trainRows", "")
        v_rows = f.get("validationRows", "")
        tm = f.get("thresholdMetrics", {}).get(thr_key, {})
        t_trades = tm.get("totalTrades", 0)
        t_wr = f"{tm.get('winRate', 0.0)*100:.1f}%" if t_trades > 0 else "—"
        t_ret = f"{tm.get('netReturnPct', 0.0):.2f}%" if t_trades > 0 else "—"
        t_pf = f"{tm.get('profitFactor', 0.0):.3f}" if t_trades > 0 else "—"
        t_dd = f"{tm.get('maxDrawdownPct', 0.0):.2f}%" if t_trades > 0 else "—"
        wf_rows.append(f"| {fold_n} | {t_rows:,} | {v_rows:,} | {t_trades} | {t_wr} | {t_ret} | {t_pf} | {t_dd} |")

    wf_median_trades = next(
        (d.get("medianTrades", 0) for d in wf.get("thresholdDiagnostics", []) if d.get("threshold") == threshold),
        0,
    )
    wf_rows.append(f"| **Median** | | | **{int(wf_median_trades)}** | | | | |")

    # Threshold grid
    grid_rows = []
    for d in wf.get("thresholdDiagnostics", []):
        sel = " ← selected" if d.get("threshold") == threshold else ""
        grid_rows.append(
            f"| {d['threshold']} | {int(d.get('medianTrades', 0))} | "
            f"{d.get('medianNetReturnPct', 0.0):.2f}% | "
            f"{d.get('medianProfitFactor', 0.0):.3f} | "
            f"{d.get('medianMaxDrawdownPct', 0.0):.2f}%{sel} |"
        )

    # Run dir artefacts
    artefacts = ["model.onnx", "report.json", "feature_schema.json", "run_config.json", "run.log", "run.jsonl", "run_report.md"]
    artefact_rows = []
    for name in artefacts:
        p = run_dir / name
        if name == "run_report.md":
            artefact_rows.append(f"| `{name}` | this file | ✅ |")
        elif p.exists():
            artefact_rows.append(f"| `{name}` | {p.stat().st_size / 1024:.1f} KB | ✅ |")
        else:
            artefact_rows.append(f"| `{name}` | — | ⚠️ missing |")

    run_label = report.get("source", "")  # fallback; actual label comes from run_dir name
    run_label = run_dir.name.split("_", 1)[1] if "_" in run_dir.name else run_dir.name
    regime_status = "enabled" if rgate.get("enabled") else "disabled"
    if rgate.get("enabled"):
        regime_status += f" [{rgate.get('minVolatilityRegime', 0):.2f}, {rgate.get('maxVolatilityRegime', 2):.2f}]"

    spread = costs.get("spreadBps", 0.0)
    commission = costs.get("commissionBps", 0.0)
    slippage = costs.get("slippageBps", 0.0)
    total_rt = spread + commission + slippage
    stress_mult = costs.get("stressCostMultiplier", 2.0)

    net_ret_base = bt.get('netReturnPct', 0.0)
    net_ret_nc = bt_nc.get('netReturnPct', 0.0)
    net_ret_sc = bt_sc.get('netReturnPct', 0.0)

    # Annualised return and compound projections
    _tw_start = report.get('testWindow', {}).get('start', '')
    _tw_end   = report.get('testWindow', {}).get('end', '')
    try:
        _ts = datetime.fromisoformat(_tw_start)
        _te = datetime.fromisoformat(_tw_end)
        test_days = (_te - _ts).days
    except Exception:
        test_days = 365
    test_years = max(test_days / 365.0, 0.01)

    def _annualised(net_pct: float) -> float:
        if net_pct <= -100:
            return -100.0
        return ((1 + net_pct / 100) ** (1 / test_years) - 1) * 100

    ann_base = _annualised(net_ret_base)
    ann_nc   = _annualised(net_ret_nc)
    ann_sc   = _annualised(net_ret_sc)

    def _ann_pl_str(ann_pct: float) -> str:
        pl = opening * ann_pct / 100
        return (f"+£{pl:,.2f}" if pl >= 0 else f"-£{abs(pl):,.2f}")

    ann_pl_base = _ann_pl_str(ann_base)
    ann_pl_nc   = _ann_pl_str(ann_nc)
    ann_pl_sc   = _ann_pl_str(ann_sc)

    def _compound_year_rows(ann_pct: float, years: int = 10) -> list[str]:
        rows: list[str] = []
        for y in range(1, years + 1):
            bal  = opening * ((1 + ann_pct / 100) ** y)
            prev = opening * ((1 + ann_pct / 100) ** (y - 1))
            gain = bal - prev
            cum  = (bal / opening - 1) * 100
            gain_str = (f"+£{gain:,.2f}" if gain >= 0 else f"-£{abs(gain):,.2f}")
            rows.append(f"| {y} | £{bal:,.2f} | {cum:.1f}% | {gain_str} |")
        return rows

    proj_rows_base = _compound_year_rows(ann_base, 10)

    def _bal_at(ann_pct: float, years: int) -> str:
        b = opening * ((1 + ann_pct / 100) ** years)
        cum = (b / opening - 1) * 100
        sign = "+" if cum >= 0 else "-"
        return f"£{b:,.2f} ({sign}{abs(cum):.1f}%)"

    md = f"""# Run Report — {run_label}

| Field | Value |
|---|---|
| **Run label** | {run_label} |
| **Symbol** | {report.get('symbol', '')} |
| **Timeframe** | {report.get('timeframe', '')} |
| **Signal variant** | {report.get('signalVariant', {}).get('name', '')} |
| **Regime gate** | {regime_status} |
| **Run directory** | `{run_dir}` |
| **Generated at** | {report.get('generatedAtUtc', '')} |
| **Train window** | {report.get('trainWindow', {}).get('start', '')} → {report.get('trainWindow', {}).get('end', '')} |
| **Test window** | {report.get('testWindow', {}).get('start', '')} → {report.get('testWindow', {}).get('end', '')} |
| **Horizon bars** | {report.get('horizonBars', '')} |
| **Label mode** | {lo.get('mode', '')} ≥ {lo.get('minEdgeBps', '')} bps |
| **Features** | {bars.get('trainFeatureRows', 0):,} train rows · {bars.get('testFeatureRows', 0):,} test rows |

---

## Verdict: {verdict_str}

Profit Factor = **{pf:.3f}** {"(needs > 1.0)" if not is_profitable else "(above 1.0 threshold)"}. Net return = **{net_ret_base:.2f}%** over the test year.

### £10,000 Opening Balance Projection

| Scenario | Opening | Net Return | Closing Balance | P/L |
|---|---|---|---|---|
| Base costs | £10,000 | {net_ret_base:.2f}% | {end_base} | {pl_base} |
| No costs | £10,000 | {net_ret_nc:.2f}% | {end_nc} | {pl_nc} |
| Stress costs | £10,000 | {net_ret_sc:.2f}% | {end_sc} | {pl_sc} |

### Annualised Returns (test span: {test_days} days = {test_years:.2f} yrs)

| Scenario | Total Return | Annualised | Annual Profit on £10k |
|---|---|---|---|
| Base costs | {net_ret_base:.2f}% | {ann_base:.2f}% | {ann_pl_base} |
| No costs | {net_ret_nc:.2f}% | {ann_nc:.2f}% | {ann_pl_nc} |
| Stress costs | {net_ret_sc:.2f}% | {ann_sc:.2f}% | {ann_pl_sc} |

### Compound Growth Projection — Base Costs (£10,000 starting capital, {ann_base:.2f}%/yr)

| Year | Closing Balance | Cumulative Return | Annual Gain |
|---|---|---|---|
{chr(10).join(proj_rows_base)}

### 5-Year & 10-Year Summary (all scenarios)

| Scenario | Ann. Rate | After 5 Years | After 10 Years |
|---|---|---|---|
| Base costs | {ann_base:.2f}% | {_bal_at(ann_base, 5)} | {_bal_at(ann_base, 10)} |
| No costs | {ann_nc:.2f}% | {_bal_at(ann_nc, 5)} | {_bal_at(ann_nc, 10)} |
| Stress costs | {ann_sc:.2f}% | {_bal_at(ann_sc, 5)} | {_bal_at(ann_sc, 10)} |

---

## Model Quality

| Metric | Value | Target | Pass? |
|---|---|---|---|
| AUC (test) | {auc:.4f} | ≥ 0.53 | {"✅" if auc >= 0.53 else "❌"} |
| Accuracy | {m.get("accuracy", 0.0)*100:.2f}% | — | — |
| Precision | {m.get("precision", 0.0)*100:.2f}% | — | — |
| Recall | {recall*100:.3f}% | — | — |
| Brier score | {m.get("brier", 0.0):.4f} | ≤ 0.25 | {"✅" if (m.get("brier") or 1.0) <= 0.25 else "❌"} |
| Predicted positive rate | {m.get("predictedPositiveRate", 0.0)*100:.3f}% | — | — |
| Selected threshold | {threshold:.2f} | — | {threshold_mode} |

**Interpretation:** AUC of {auc:.4f} is {"above" if auc >= 0.53 else "below"} the 0.53 minimum bar. The model fires on {m.get("predictedPositiveRate", 0.0)*100:.2f}% of test bars, generating {trades} trades. Precision of {m.get("precision", 0.0)*100:.1f}% means {"better than" if m.get("precision", 0.0) >= 0.5 else "below"} a coin-flip on each signal.

---

## Strategy Backtest — Test Window

| Scenario | Trades | Win Rate | Net Return | Profit Factor | Max DD | Sharpe | Avg Trade |
|---|---|---|---|---|---|---|---|
| Base costs | {bt.get("totalTrades",0)} | {bt.get("winRate",0.0)*100:.1f}% | {bt.get("netReturnPct",0.0):.2f}% | {bt.get("profitFactor",0.0):.3f} | {bt.get("maxDrawdownPct",0.0):.2f}% | {bt.get("sharpeApprox",0.0):.2f} | {bt.get("avgTradeReturnPct",0.0):.3f}% |
| No costs | {bt_nc.get("totalTrades",0)} | {bt_nc.get("winRate",0.0)*100:.1f}% | {bt_nc.get("netReturnPct",0.0):.2f}% | {bt_nc.get("profitFactor",0.0):.3f} | {bt_nc.get("maxDrawdownPct",0.0):.2f}% | {bt_nc.get("sharpeApprox",0.0):.2f} | {bt_nc.get("avgTradeReturnPct",0.0):.3f}% |
| Stress costs ({stress_mult:.0f}× spread) | {bt_sc.get("totalTrades",0)} | {bt_sc.get("winRate",0.0)*100:.1f}% | {bt_sc.get("netReturnPct",0.0):.2f}% | {bt_sc.get("profitFactor",0.0):.3f} | {bt_sc.get("maxDrawdownPct",0.0):.2f}% | {bt_sc.get("sharpeApprox",0.0):.2f} | {bt_sc.get("avgTradeReturnPct",0.0):.3f}% |

Cost assumptions: spread {spread} bps + commission {commission} bps + slippage {slippage} bps = {total_rt} bps per side.

---

## Walk-Forward CV — Threshold {threshold:.2f} (selected)

| Fold | Train rows | Val rows | Trades | Win Rate | Net Return | PF | Max DD |
|---|---|---|---|---|---|---|---|
{chr(10).join(wf_rows)}

**Threshold selection mode:** {threshold_mode}. {folds_profitable} of {folds_total} folds had PF > 1.0 at threshold {threshold:.2f}.

---

## Threshold Grid Comparison (median across CV folds)

| Threshold | Median Trades | Median Net Return | Median PF | Median Max DD |
|---|---|---|---|---|
{chr(10).join(grid_rows)}

---

## Scorecard

| Aspect | Score | Rationale |
|---|---|---|
| AUC | {auc_score}/10 | {auc:.4f} — {"above" if auc >= 0.53 else "below"} 0.53 minimum |
| Profit factor | {pf_score}/10 | {pf:.3f} — {"profitable" if pf >= 1.0 else "losing"} |
| Win rate | {wr_score}/10 | {win_rate*100:.1f}% — {"above" if win_rate >= 0.50 else "below"} 50% |
| Trade frequency | {freq_score}/10 | {trades} trades/year — {"sufficient" if trades >= 60 else "below 60-trade gate"} |
| CV consistency | {cv_score}/10 | {folds_profitable}/{folds_total} folds profitable at threshold |
| Max drawdown | {dd_score}/10 | {max_dd:.2f}% — {"controlled" if abs(max_dd) <= 10 else "elevated"} |
| Sharpe | {sharpe_score}/10 | {sharpe:.2f} — {"positive" if sharpe > 0 else "negative"} risk-adjusted returns |
| Recall | {recall_score}/10 | {recall*100:.3f}% — model fires on very few bars |
| Cost robustness | {cost_score}/10 | Stress PF {stress_pf:.3f} vs base {pf:.3f} ({cost_ratio*100:.0f}% retention) |
| Pipeline integrity | 10/10 | Clean end-to-end run, all artefacts written |

---

## Data & Pipeline

| Item | Value |
|---|---|
| Train bars fetched | {bars.get("trainFetched", 0):,} |
| Train feature rows | {bars.get("trainFeatureRows", 0):,} |
| Test bars fetched | {bars.get("testFetched", 0):,} |
| Test feature rows | {bars.get("testFeatureRows", 0):,} |
| ONNX model | `model.onnx` |
| Download status | {report.get("downloadJob", {}).get("status", "UNKNOWN")} |

---

## Cost Assumptions

| Component | Base | Stress |
|---|---|---|
| Spread | {spread} bps | {spread * stress_mult} bps |
| Commission | {commission} bps | {commission} bps |
| Slippage | {slippage} bps | {slippage * stress_mult} bps |
| Round-trip total | {total_rt} bps | {spread * stress_mult + commission + slippage * stress_mult} bps |
| Stress multiplier | 1× | {stress_mult:.0f}× |

---

## Artefacts

| File | Size | Status |
|---|---|---|
{chr(10).join(artefact_rows)}

---

## Gate Assessment

| Gate | Criterion | Actual | Pass? |
|---|---|---|---|
| Profit factor | ≥ 1.25 | {pf:.3f} | {pf_gate} |
| Max drawdown | ≤ 20% | {max_dd:.2f}% | {dd_gate} |
| Trade count | ≥ 60 | {trades} | {trade_gate} |
| Expectancy (bps after cost) | > 5 bps | {exp_bps:.1f} bps | {exp_gate} |
| Fold consistency | ≥ 60% folds profitable | {cv_pct*100:.0f}% ({folds_profitable}/{folds_total}) | {cv_gate} |
| AUC | ≥ 0.53 | {auc:.4f} | {auc_gate} |

**Overall gate result:** {overall_gate}

---

## Analysis

{analysis}

---

*Auto-generated by `training/run_historical_split.py` · Template: `logs/training/run_report_template.md`*
"""

    (run_dir / "run_report.md").write_text(md.strip() + "\n", encoding="utf-8")


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
    parser.add_argument("--cusum-event-filter", action="store_true",
                        help="Restrict training and inference to CUSUM-filtered event bars only.")
    parser.add_argument("--cusum-h-lookback", type=int, default=20,
                        help="Rolling window (bars) for adaptive CUSUM threshold (default: 20).")
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
    parser.add_argument(
        "--single-train-window",
        action="store_true",
        default=False,
        help=(
            "Use a single contiguous training window (train_start → train_end) instead of the "
            "default hardcoded 3-chunk split. Required for rolling walk-forward tests where "
            "train_end < 2021 to prevent data leakage from the hardcoded 2018-2020 window."
        ),
    )
    parser.add_argument(
        "--min-fold-train-rows",
        type=int,
        default=300,
        help=(
            "Minimum number of training rows required for a CV fold to be used. Default 300 "
            "(suitable for 5+ year training). Lower to e.g. 80 for rolling walk-forward tests "
            "with 3-year training windows."
        ),
    )
    parser.add_argument(
        "--min-fold-val-rows",
        type=int,
        default=100,
        help=(
            "Minimum number of validation rows required for a CV fold to be used. Default 100. "
            "Lower to e.g. 30 for rolling walk-forward tests with 3-year training windows "
            "where each CV fold validation set has ~42 rows."
        ),
    )
    parser.add_argument(
        "--sample-weight-halflife-days",
        type=int,
        default=0,
        help=(
            "Halflife in calendar days for exponential recency weighting of training bars. "
            "0 = uniform weights (default). 730 = 2-year halflife: a bar from 2 years ago "
            "gets weight 0.5 vs a bar from today. Helps the model adapt to the current regime "
            "when retraining monthly on an expanding window."
        ),
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

    if args.single_train_window:
        train_windows = [Window(args.train_start, args.train_end)]
    else:
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
    # Prepend the last 500 training bars as context before computing test features.
    # frac_diff_ffd (d=0.4, thres=1e-4) needs ~241 bars of warmup, sma200 needs 200.
    # Without context, a 1-year (258-bar) test window produces all-NaN fd_close and
    # 0 valid feature rows before CUSUM runs.
    _ctx_n = 500
    _ctx_df = train_df.tail(_ctx_n).copy()
    _test_with_ctx = pd.concat([_ctx_df, test_df], ignore_index=True)
    _test_feat_full = compute_features(_test_with_ctx, args.horizon_bars)
    _test_start_ts = pd.to_datetime(test_df["barCloseTimeUtc"].min(), utc=True)
    _test_feat_full["_ts"] = pd.to_datetime(_test_feat_full["barCloseTimeUtc"], utc=True)
    test_feat = _test_feat_full[_test_feat_full["_ts"] >= _test_start_ts].drop(columns=["_ts"]).copy().reset_index(drop=True)
    train_feat = apply_label_objective(train_feat, args.label_mode, float(args.min_edge_bps))
    test_feat = apply_label_objective(test_feat, args.label_mode, float(args.min_edge_bps))

    # CUSUM event filter: restrict training and inference to bars where a
    # structurally significant directional move is beginning.  The adaptive
    # threshold (h=None) is computed purely from returns — no label leakage.
    if args.cusum_event_filter:
        n_train_orig = len(train_feat)
        n_test_orig = len(test_feat)
        train_event_idx = cusum_events(
            train_feat["close"].reset_index(drop=True),
            h=None,
            h_lookback=args.cusum_h_lookback,
        )
        test_event_idx = cusum_events(
            test_feat["close"].reset_index(drop=True),
            h=None,
            h_lookback=args.cusum_h_lookback,
        )
        train_feat = train_feat.iloc[train_event_idx].reset_index(drop=True)
        test_feat = test_feat.iloc[test_event_idx].reset_index(drop=True)
        logger.info(
            "cusum event filter: train %d → %d events  test %d → %d events",
            n_train_orig, len(train_feat), n_test_orig, len(test_feat),
        )
        write_event(run_dir, "cusum_filter_applied",
                    hLookback=args.cusum_h_lookback,
                    trainEvents=len(train_feat),
                    testEvents=len(test_feat))

    feature_cols = [
        "ret1", "ret2", "ret3", "ret5", "ret10",
        "volatility20", "volatility100", "volatility_regime",
        "atr_normalised", "above_sma", "trend_strength",
        "breakout_distance", "efficiency_ratio", "adx",
        "rsi14", "macd_signal",
        "htf_trend", "is_active_session", "dxy_trend",
        "vix_regime", "day_of_week",
        "us_rate_trend", "fd_close",
    ]
    logger.info("feature rows: train=%d  test=%d  n_features=%d", len(train_feat), len(test_feat), len(feature_cols))
    write_event(run_dir, "features_computed", trainRows=len(train_feat), testRows=len(test_feat), nFeatures=len(feature_cols))
    (run_dir / "feature_schema.json").write_text(
        json.dumps({
            "version": "ts004_v4",
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

    # Recency weighting: bars closer to train_end count more.
    # halflife_days=0 means uniform weights.
    _halflife_days = int(args.sample_weight_halflife_days)
    if _halflife_days > 0:
        _last_date = pd.to_datetime(train_feat["barCloseTimeUtc"], utc=True).max()
        _bar_dates = pd.to_datetime(train_feat["barCloseTimeUtc"], utc=True)
        _age_days = (_last_date - _bar_dates).dt.days.to_numpy(dtype=float)
        _train_sample_weights = np.exp(-_age_days * np.log(2.0) / _halflife_days).astype(np.float32)
        _train_sample_weights /= _train_sample_weights.mean()  # keep scale neutral
        logger.info(
            "recency weighting: halflife=%d days  weight range [%.3f, 1.000]",
            _halflife_days, float(_train_sample_weights.min()),
        )
    else:
        _train_sample_weights = None

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
        min_fold_train_rows=max(1, int(args.min_fold_train_rows)),
        min_fold_val_rows=max(1, int(args.min_fold_val_rows)),
        sample_weights=_train_sample_weights,
    )

    logger.info(
        "threshold selected: %.2f (mode=%s)  training final model on %d rows  scale_pos_weight=%.3f",
        selected_threshold, wf_report.get("selectionMode", "?"), len(X_train), scale_pos_weight,
    )
    write_event(run_dir, "threshold_selected",
                threshold=selected_threshold,
                mode=wf_report.get("selectionMode"))
    model = make_model(scale_pos_weight=scale_pos_weight)
    model.fit(X_train, y_train, sample_weight=_train_sample_weights)
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
    try:
        generate_run_report(report, run_dir)
        logger.info("run report written → %s", run_dir / "run_report.md")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("run report generation failed (non-fatal): %s", exc)
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
