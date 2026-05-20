import type { DecisionAction, SignalRequest } from "../types/contracts";

export function evaluateDailyBreakout(input: SignalRequest): DecisionAction {
  const m = input.marketSnapshot;

  const longSignal = m.close1 > m.sma200_1 && m.close1 > m.highestHigh55;
  const shortSignal = m.close1 < m.sma200_1 && m.close1 < m.lowestLow55;

  if (longSignal) {
    return "BUY";
  }

  if (shortSignal) {
    return "SELL";
  }

  return "HOLD";
}
