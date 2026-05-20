import type { SignalRequest } from "../types/contracts";

export interface SetupCandidate {
  direction: "LONG" | "SHORT" | "NONE";
  confidence?: number;
}

export interface SetupScore {
  score: number;
  bucket: "FULL" | "HALF" | "SKIP";
}

export interface TradePlan {
  action: "BUY" | "SELL" | "HOLD" | "CLOSE" | "REDUCE";
  sizeMultiplier: number;
  reasons: string[];
}

export interface StrategyPlugin {
  id: string;
  version: string;
  evaluate(input: SignalRequest): TradePlan;
}
