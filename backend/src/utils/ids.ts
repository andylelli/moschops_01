import { v4 as uuidv4 } from "uuid";

export function newSignalId(): string {
  return uuidv4();
}

export function decisionKey(strategyId: string, symbol: string, timeframe: string, barCloseTimeUtc: string): string {
  return `${strategyId}:${symbol}:${timeframe}:${barCloseTimeUtc}`;
}
