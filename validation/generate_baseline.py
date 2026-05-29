#!/usr/bin/env python3
"""Generate Phase 5 baseline validation report."""

from pathlib import Path
from backtest_engine import BacktestParams, make_synthetic_bars, calculate_indicators, generate_signals, run_backtest, generate_report

def main():
    # Standard v1.0 parameters
    params = BacktestParams(
        symbol="EURUSD",
        start_date="2023-01-01",
        end_date="2023-12-31",
        starting_capital=10000.0,
        risk_per_trade=0.005,  # 0.5%
        lookback_periods=55,
        atr_period=20,
        sma_fast=100,
        sma_trend=200,
        spread_pips=2.0,
        slippage_pips=1.0,
        commission_pct=0.0002,
    )

    print("Phase 5: Baseline Backtesting & Validation")
    print(f"Generating synthetic data for {params.symbol}...")
    df = make_synthetic_bars(days=252, start_price=1.1000, trend=0.0001, volatility=0.008, seed=42)

    print("Calculating indicators...")
    df = calculate_indicators(df, params)

    print("Generating signals...")
    df = generate_signals(df)

    print("Running backtest...")
    trades, stats = run_backtest(df, params)

    print(f"\nResults: {stats.total_trades} trades, {stats.win_rate * 100:.1f}% win rate, ${stats.net_profit:.2f} profit")
    print(f"Profit factor: {stats.profit_factor:.2f} | Sharpe: {stats.sharpe_ratio:.2f} | Max DD: {stats.drawdown_pct:.2f}%")

    print("\nGenerating report...")
    report = generate_report(params, stats, trades)

    output_path = Path(__file__).parent / "baseline.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    main()
