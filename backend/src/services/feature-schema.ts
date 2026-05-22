export const RUNTIME_FEATURE_SCHEMA = [
  "trend_strength",
  "volatility",
  "spread_atr",
  "breakout_distance",
  "momentum",
] as const;

export interface MarketSnapshotFeaturesInput {
  close1: number;
  sma100_1: number;
  sma200_1: number;
  highestHigh55: number;
  atr20_1: number;
  volatility: number;
  spreadPrice?: number;
}

export function buildInferenceFeatures(input: MarketSnapshotFeaturesInput): number[] {
  return [
    input.close1 - input.sma200_1,
    input.volatility,
    (input.spreadPrice ?? 0) / Math.max(input.atr20_1, 0.000001),
    input.close1 - input.highestHigh55,
    input.close1 - input.sma100_1,
  ];
}
