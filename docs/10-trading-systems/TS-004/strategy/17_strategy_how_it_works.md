# 17 Strategy How It Works

System ID: TS-004
Version: 1.0
Last updated: 2026-05-28

## What this strategy does (plain language)

TS-004 looks for opportunities to trade with the trend on the EURO/US Dollar (EURUSD) currency pair using 4-hour charts. Its specific insight is that after a major news event (like a US jobs report, inflation data, or central bank announcement), markets often react sharply and then calm down — and when they calm down, the trend that existed before the event tends to resume. TS-004 tries to capture those resumption moves.

## The big picture

Imagine the market as a river. Most of the time, the river flows in one direction (the trend). Sometimes, a big rock is thrown in (a news event), causing a temporary splash and turbulence. Once the turbulence settles and the water returns to normal flow, the river continues in its original direction. TS-004 waits for the "turbulence" to settle and then enters in the direction the river was already flowing.

## How the AI works

An AI model (XGBoost) is trained on years of historical EURUSD 4-hour data. It looks at a set of mathematical signals at each bar close and estimates the probability that the next 10 bars (approximately 40 hours) will produce a meaningful move in the trend direction (8 basis points or more).

The AI was trained only on historical data up to 2022 and tested on 2023–2024 data it has never seen. This prevents it from being "fitted" to recent history and makes its conclusions more reliable.

## The volatility gate — the key innovation

The most important feature in TS-004 is the **volatility regime ratio**: the current short-term volatility divided by the longer-term average volatility.

- **Below 0.80** (market too quiet): No major event has occurred recently. No entry. The thesis requires an event to have happened.
- **Between 0.80 and 2.00** (normalisation window): The market has been through some turbulence and is now calming down. This is the entry window. The AI evaluates the signal quality and can trigger an entry.
- **Above 2.00** (event still active): The market is still very volatile. Spreads are wide, false breakouts are common. No entry. The event hasn't resolved yet.

This gate is the heart of the strategy. It acts as an automatic "news event detector" without needing access to a news calendar.

## The trend filter — which way to trade

Before entering, TS-004 also checks that:
1. The price is above the 200-bar moving average (for long trades) or below it (for short trades).
2. The trend strength score is meaningful (not trading into a flat, directionless market).

This means TS-004 only trades in the direction the market has been trending for approximately the last 5 months. It does not try to call reversals.

## What makes a good entry

A trade is taken only when **all three conditions** are met simultaneously:
1. Volatility regime is in the normalisation window [0.80 – 2.00]
2. AI confidence (probability) is above the selected threshold
3. Price is aligned with the long-term trend direction

## Risk management — how losses are controlled

Every trade has a stop loss set at 1.5 times the current Average True Range (ATR) — a measure of recent bar size. This means the stop is automatically wider in volatile markets and tighter in quiet ones.

There is also a **circuit breaker** that pauses all trading if:
- Daily losses exceed 1.5% of account equity
- Drawdown from the peak exceeds 15%
- 4 consecutive trades are losing trades

The circuit breaker cooldown lasts approximately 3.5 trading days (20 bars of H4 time). This prevents the strategy from compounding losses during adverse conditions.

## What TS-004 does NOT do

- It does not trade based on news headlines or event calendars.
- It does not use overnight sentiment, COT positioning, or alternative data.
- It does not trade more than one position at a time.
- It does not try to predict the direction of an event — only the continuation after it.
- It does not react to tick-by-tick price movements (only acts at the close of each 4-hour bar).

## How it connects to the rest of the platform

- The AI model runs in the backend (a local server on port 3000).
- The MetaTrader 5 trading platform runs an automated trading script (EA — Expert Advisor) that asks the backend for a signal at each 4-hour bar close.
- If the signal passes all checks, the EA places a trade automatically.
- All signals and outcomes are logged to a database for monitoring and future model improvement.

## The journey from idea to live trading

| Step | What happens |
|---|---|
| 1. Discovery | Run experiments on historical data (2012–2022) |
| 2. Holdout validation | Test once on 2023–2024 data (never tuned on this) |
| 3. Paper trading | Run signals live but without real money for 30 days |
| 4. Micro-live | Trade very small positions ($0.01 per pip) |
| 5. Full live | Scale up position sizes after sustained profitability |

TS-004 is currently at **Step 1 (Discovery)**. No money has been traded yet.
