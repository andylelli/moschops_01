import type { StrategyPlugin } from "./strategy-plugin";
import type { SignalRequest } from "../types/contracts";

export const dailyBreakout510: StrategyPlugin = {
  id: "daily-breakout-5-10",
  version: "1.0.0",
  evaluate(input: SignalRequest) {
    const m = input.marketSnapshot;
    const longSignal = m.close1 > m.sma200_1 && m.close1 > m.highestHigh55;
    const shortSignal = m.close1 < m.sma200_1 && m.close1 < m.lowestLow55;

    if (longSignal) {
      return { action: "BUY", sizeMultiplier: 1, reasons: ["BREAKOUT_LONG"] };
    }

    if (shortSignal) {
      return { action: "SELL", sizeMultiplier: 1, reasons: ["BREAKOUT_SHORT"] };
    }

    return { action: "HOLD", sizeMultiplier: 0, reasons: ["NO_SETUP"] };
  },
};

export function scoreSetup(input: SignalRequest): { score: number; bucket: "FULL" | "HALF" | "SKIP" } {
  const aiScore = input.aiScore ?? 0;
  if (aiScore >= 0.65) {
    return { score: aiScore, bucket: "FULL" };
  }

  if (aiScore >= 0.55) {
    return { score: aiScore, bucket: "HALF" };
  }

  return { score: aiScore, bucket: "SKIP" };
}
