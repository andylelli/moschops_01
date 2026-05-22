import { createHash } from "node:crypto";
import { env } from "../utils/env";

export type NewsPolicyAction = "ALLOW" | "REDUCE" | "BLOCK_NEW";
export type NewsSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type NewsFreshnessState = "FRESH" | "DEGRADED" | "STALE" | "DOWN";

export const NEWS_PROVIDER = "FMP";

export interface SeverityPolicyWindow {
  action: NewsPolicyAction;
  reasonCode: string;
  preMinutes: number;
  postMinutes: number;
}

const SEVERITY_POLICY: Record<NewsSeverity, SeverityPolicyWindow> = {
  LOW: { action: "ALLOW", reasonCode: "NEWS_ALLOW_LOW_IMPACT", preMinutes: 0, postMinutes: 0 },
  MEDIUM: { action: "REDUCE", reasonCode: "NEWS_REDUCE_MEDIUM_IMPACT", preMinutes: 15, postMinutes: 30 },
  HIGH: { action: "BLOCK_NEW", reasonCode: "NEWS_BLOCK_HIGH_IMPACT", preMinutes: 30, postMinutes: 60 },
  CRITICAL: { action: "BLOCK_NEW", reasonCode: "NEWS_BLOCK_HIGH_IMPACT", preMinutes: 30, postMinutes: 60 },
};

export function getSeverityPolicy(severity: NewsSeverity): SeverityPolicyWindow {
  return SEVERITY_POLICY[severity];
}

export function parseEnabledSymbols(): string[] {
  return env.NEWS_ENABLED_SYMBOLS.split(",")
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export function getSymbolCurrencyExposure(symbol: string): string[] {
  const normalized = symbol.trim().toUpperCase();

  if (normalized.length >= 6) {
    const base = normalized.slice(0, 3);
    const quote = normalized.slice(3, 6);
    return [base, quote];
  }

  return [];
}

export function hasCompleteSymbolMapping(symbols: string[]): boolean {
  return symbols.every((symbol) => getSymbolCurrencyExposure(symbol).length > 0);
}

export function impactedSymbolsForCurrency(currencyCode: string | null | undefined, symbols: string[]): string[] {
  if (!currencyCode) {
    return [];
  }

  const currency = currencyCode.toUpperCase();
  return symbols.filter((symbol) => getSymbolCurrencyExposure(symbol).includes(currency));
}

export function normalizeImpact(impact: string | null | undefined): NewsSeverity {
  const source = (impact ?? "").trim().toLowerCase();

  if (source === "high") {
    return "HIGH";
  }

  if (source === "medium") {
    return "MEDIUM";
  }

  if (source === "low") {
    return "LOW";
  }

  return "CRITICAL";
}

export function buildFallbackProviderEventId(input: {
  date: string;
  event: string;
  country?: string | null;
  currency?: string | null;
}): string {
  const stableKey = [input.date, input.event, input.country ?? "", input.currency ?? ""].join("|");
  const hash = createHash("sha256").update(stableKey).digest("hex").slice(0, 24);
  return `fmp-${hash}`;
}

export function isEntryAction(action: string): boolean {
  return action === "BUY" || action === "SELL";
}

export function computeFreshnessState(lastSuccessfulSyncUtc: Date | null | undefined, now = new Date()): NewsFreshnessState {
  if (!lastSuccessfulSyncUtc) {
    return "DOWN";
  }

  const deltaMinutes = (now.getTime() - lastSuccessfulSyncUtc.getTime()) / 60000;

  if (deltaMinutes >= env.NEWS_STALE_MINUTES) {
    return "STALE";
  }

  if (deltaMinutes >= env.NEWS_DEGRADED_MINUTES) {
    return "DEGRADED";
  }

  return "FRESH";
}
