export type DecisionAction = "BUY" | "SELL" | "HOLD" | "CLOSE" | "REDUCE";

export interface MarketSnapshot {
  symbol: string;
  timeframe: string;
  barCloseTimeUtc: string;
  close1: number;
  sma100_1: number;
  sma200_1: number;
  highestHigh55: number;
  lowestLow55: number;
  atr20_1: number;
  volatility: number;
  spreadPrice?: number;
  open0?: number;
  close1Prev?: number;
}

export interface AccountSnapshot {
  accountId: string;
  equity?: number;
  balance?: number;
  openRisk?: number;
  openTrades?: number;
  dailyLossPct?: number;
  weeklyLossPct?: number;
}

export interface SignalRequest {
  decisionId: string;
  strategyId: string;
  strategyVersion: string;
  modelVersion?: string;
  symbol: string;
  timeframe: string;
  barCloseTimeUtc: string;
  marketSnapshot: MarketSnapshot;
  accountSnapshot: AccountSnapshot;
  aiScore?: number;
}

export interface SignalResponse {
  decisionId: string;
  signalId: string;
  action: DecisionAction;
  riskDecision: "APPROVED" | "VETOED";
  reasonCodes: string[];
  barCloseTimeUtc: string;
  evaluatedAtUtc: string;
}

export interface RiskCheckRequest {
  decisionId: string;
  strategyId: string;
  symbol: string;
  accountSnapshot: AccountSnapshot;
  proposedRiskPct: number;
  proposedOpenTrades: number;
  maxOpenRisk?: number;
  maxOpenTrades?: number;
  dailyLossLimitPct?: number;
  weeklyLossLimitPct?: number;
}

export interface RiskCheckResponse {
  approved: boolean;
  vetoReasonCodes: string[];
  adjustedSize: number;
  evaluatedAtUtc: string;
}
