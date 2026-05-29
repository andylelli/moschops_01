# 04 Feature Schema (Template)

System ID: TS-XXX

## Feature registry
| Feature | Formula | Inputs | Window | Leakage risk | Runtime parity check |
|---|---|---|---|---|---|
| <feature> | <formula> | <inputs> | <lookback> | <low/med/high> | <how validated> |

## Feature groups
1. Trend features:
2. Volatility features:
3. Execution/cost context features:
4. Optional macro/news features:

## Feature computation policy
1. Completed-bar only policy:
2. Shift policy for derived fields:
3. Imputation policy:

## Schema lock policy
1. Feature names immutable per model version.
2. Order and type contract enforced.
3. Runtime mismatch handling policy.
