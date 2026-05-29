import type { Prisma } from "@prisma/client";
import { prismaClient } from "./prisma";
import {
  NEWS_PROVIDER,
  buildFallbackProviderEventId,
  computeFreshnessState,
  getSeverityPolicy,
  hasCompleteSymbolMapping,
  impactedSymbolsForCurrency,
  normalizeImpact,
  parseEnabledSymbols,
} from "./news-domain";
import { env } from "../utils/env";
import { recordFileLog } from "./file-log";

interface LoggerLike {
  info: (obj: unknown, msg?: string) => void;
  warn: (obj: unknown, msg?: string) => void;
  error: (obj: unknown, msg?: string) => void;
}

interface FmpEconomicCalendarRow {
  date: string;
  country?: string | null;
  event: string;
  currency?: string | null;
  previous?: number | null;
  estimate?: number | null;
  actual?: number | null;
  change?: number | null;
  impact?: string | null;
  changePercentage?: number | null;
  unit?: string | null;
}

class ProviderAccessDeniedError extends Error {
  constructor(
    readonly statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "ProviderAccessDeniedError";
  }
}

function asUtcDate(value: string): Date | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  let normalized = trimmed.includes("T") ? trimmed : trimmed.replace(" ", "T");
  if (!normalized.endsWith("Z")) {
    normalized = `${normalized}Z`;
  }

  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed;
}

function asOptionalNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function toDateStringUtc(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function isSameUtcDay(a: Date, b: Date): boolean {
  return a.toISOString().slice(0, 10) === b.toISOString().slice(0, 10);
}

async function fetchEconomicCalendarRows(from: string, to: string): Promise<FmpEconomicCalendarRow[]> {
  const apiKey = env.FMP_API_KEY;
  if (!apiKey) {
    throw new Error("FMP_API_KEY missing");
  }

  const origin = new URL(env.FMP_BASE_URL).origin;

  const primaryUrl = new URL("/stable/economic-calendar", origin);
  primaryUrl.searchParams.set("from", from);
  primaryUrl.searchParams.set("to", to);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    let response = await fetch(primaryUrl, {
      method: "GET",
      headers: {
        apikey: apiKey,
      },
      signal: controller.signal,
    });

    if (response.status === 401 || response.status === 403) {
      const fallbackUrl = new URL(primaryUrl);
      fallbackUrl.searchParams.set("apikey", apiKey);
      response = await fetch(fallbackUrl, { signal: controller.signal });
    }

    if (!response.ok) {
      const body = await response.text();
      const message = `FMP request failed (${response.status}): ${body.slice(0, 250)}`;
      if (response.status === 401 || response.status === 402 || response.status === 403) {
        throw new ProviderAccessDeniedError(response.status, message);
      }
      throw new Error(message);
    }

    const payload = (await response.json()) as unknown;
    if (!Array.isArray(payload)) {
      throw new Error("Unexpected FMP response shape for economic-calendar");
    }

    return payload as FmpEconomicCalendarRow[];
  } finally {
    clearTimeout(timeout);
  }
}

async function upsertProviderStatus(data: Prisma.NewsProviderStatusUpsertArgs["create"]): Promise<void> {
  await prismaClient().newsProviderStatus.upsert({
    where: { provider: NEWS_PROVIDER },
    create: data,
    update: {
      lastSuccessfulSyncUtc: data.lastSuccessfulSyncUtc,
      lastAttemptedSyncUtc: data.lastAttemptedSyncUtc,
      freshnessState: data.freshnessState,
      failureReason: data.failureReason,
      budgetUsed: data.budgetUsed,
      budgetLimit: data.budgetLimit,
    },
  });
}

export async function syncNewsNow(log: LoggerLike): Promise<void> {
  const now = new Date();
  const symbols = parseEnabledSymbols();

  if (!env.NEWS_SYNC_ENABLED) {
    await upsertProviderStatus({
      provider: NEWS_PROVIDER,
      lastSuccessfulSyncUtc: null,
      lastAttemptedSyncUtc: now,
      freshnessState: "DOWN",
      failureReason: "NEWS_SYNC_DISABLED",
      budgetUsed: 0,
      budgetLimit: env.NEWS_BUDGET_DAILY,
    });
    recordFileLog({
      category: "news",
      level: "info",
      event: "news_sync_disabled",
      message: "news sync disabled",
      context: { budgetUsed: 0, budgetLimit: env.NEWS_BUDGET_DAILY },
    });
    return;
  }

  if (!hasCompleteSymbolMapping(symbols)) {
    await upsertProviderStatus({
      provider: NEWS_PROVIDER,
      lastSuccessfulSyncUtc: null,
      lastAttemptedSyncUtc: now,
      freshnessState: "DOWN",
      failureReason: "SYMBOL_MAPPING_INCOMPLETE",
      budgetUsed: 0,
      budgetLimit: env.NEWS_BUDGET_DAILY,
    });
    recordFileLog({
      category: "news",
      level: "warn",
      event: "news_sync_skipped",
      message: "news sync skipped because symbol mapping is incomplete",
      context: { failureReason: "SYMBOL_MAPPING_INCOMPLETE" },
    });
    return;
  }

  const existing = await prismaClient().newsProviderStatus.findUnique({ where: { provider: NEWS_PROVIDER } });
  const previousBudgetUsed = existing?.lastAttemptedSyncUtc && isSameUtcDay(existing.lastAttemptedSyncUtc, now) ? existing.budgetUsed ?? 0 : 0;

  const reserveFloor = Math.ceil(env.NEWS_BUDGET_DAILY * (env.NEWS_BUDGET_RESERVE_PCT / 100));
  const usableBudget = Math.max(1, env.NEWS_BUDGET_DAILY - reserveFloor);

  if (previousBudgetUsed >= usableBudget) {
    await upsertProviderStatus({
      provider: NEWS_PROVIDER,
      lastSuccessfulSyncUtc: existing?.lastSuccessfulSyncUtc ?? null,
      lastAttemptedSyncUtc: now,
      freshnessState: "DEGRADED",
      failureReason: "BUDGET_RESERVE_PROTECTED",
      budgetUsed: previousBudgetUsed,
      budgetLimit: env.NEWS_BUDGET_DAILY,
    });
    recordFileLog({
      category: "news",
      level: "warn",
      event: "news_sync_budget_blocked",
      message: "news sync blocked by reserve budget protection",
      context: { budgetUsed: previousBudgetUsed, budgetLimit: env.NEWS_BUDGET_DAILY },
    });
    return;
  }

  const nextBudgetUsed = previousBudgetUsed + 1;

  try {
    const fromDate = new Date(now);
    fromDate.setUTCDate(fromDate.getUTCDate() - env.NEWS_LOOKBACK_DAYS);

    const toDate = new Date(now);
    toDate.setUTCDate(toDate.getUTCDate() + env.NEWS_LOOKAHEAD_DAYS);

    const rows = await fetchEconomicCalendarRows(toDateStringUtc(fromDate), toDateStringUtc(toDate));

    for (const row of rows) {
      const scheduledAtUtc = asUtcDate(row.date);
      if (!scheduledAtUtc) {
        continue;
      }

      const severity = normalizeImpact(row.impact);
      const policy = getSeverityPolicy(severity);
      const providerEventId = buildFallbackProviderEventId({
        date: row.date,
        event: row.event,
        country: row.country,
        currency: row.currency,
      });

      const event = await prismaClient().newsEvent.upsert({
        where: {
          provider_providerEventId: {
            provider: NEWS_PROVIDER,
            providerEventId,
          },
        },
        create: {
          provider: NEWS_PROVIDER,
          providerEventId,
          eventType: row.event,
          title: row.event,
          countryCode: row.country ?? null,
          currencyCode: row.currency ?? null,
          severity,
          scheduledAtUtc,
          forecastValue: asOptionalNumber(row.estimate),
          previousValue: asOptionalNumber(row.previous),
          actualValue: asOptionalNumber(row.actual),
          status: row.actual == null ? "SCHEDULED" : "COMPLETED",
          rawJson: row as unknown as Prisma.InputJsonValue,
          normalizedJson: {
            unit: row.unit ?? null,
            change: asOptionalNumber(row.change),
            changePercentage: asOptionalNumber(row.changePercentage),
          } as Prisma.InputJsonValue,
        },
        update: {
          eventType: row.event,
          title: row.event,
          countryCode: row.country ?? null,
          currencyCode: row.currency ?? null,
          severity,
          scheduledAtUtc,
          forecastValue: asOptionalNumber(row.estimate),
          previousValue: asOptionalNumber(row.previous),
          actualValue: asOptionalNumber(row.actual),
          status: row.actual == null ? "SCHEDULED" : "COMPLETED",
          rawJson: row as unknown as Prisma.InputJsonValue,
          normalizedJson: {
            unit: row.unit ?? null,
            change: asOptionalNumber(row.change),
            changePercentage: asOptionalNumber(row.changePercentage),
          } as Prisma.InputJsonValue,
        },
      });

      const impactedSymbols = impactedSymbolsForCurrency(row.currency, symbols);
      for (const symbol of impactedSymbols) {
        const startsAtUtc = new Date(scheduledAtUtc.getTime() - policy.preMinutes * 60_000);
        const endsAtUtc = new Date(scheduledAtUtc.getTime() + policy.postMinutes * 60_000);

        await prismaClient().newsGuardWindow.upsert({
          where: {
            newsEventId_symbolScope_policyAction: {
              newsEventId: event.newsEventId,
              symbolScope: symbol,
              policyAction: policy.action,
            },
          },
          create: {
            newsEventId: event.newsEventId,
            symbolScope: symbol,
            currencyScope: row.currency ?? null,
            policyAction: policy.action,
            startsAtUtc,
            endsAtUtc,
            severity,
            reasonCode: policy.reasonCode,
            metadataJson: {
              provider: NEWS_PROVIDER,
              title: row.event,
            } as Prisma.InputJsonValue,
          },
          update: {
            currencyScope: row.currency ?? null,
            startsAtUtc,
            endsAtUtc,
            severity,
            reasonCode: policy.reasonCode,
            metadataJson: {
              provider: NEWS_PROVIDER,
              title: row.event,
            } as Prisma.InputJsonValue,
          },
        });
      }
    }

    await upsertProviderStatus({
      provider: NEWS_PROVIDER,
      lastSuccessfulSyncUtc: now,
      lastAttemptedSyncUtc: now,
      freshnessState: "FRESH",
      failureReason: null,
      budgetUsed: nextBudgetUsed,
      budgetLimit: env.NEWS_BUDGET_DAILY,
    });

    log.info({ rows: rows.length, budgetUsed: nextBudgetUsed }, "news sync completed");
    recordFileLog({
      category: "news",
      level: "info",
      event: "news_sync_completed",
      message: "news sync completed",
      context: { rows: rows.length, budgetUsed: nextBudgetUsed },
    });
  } catch (error) {
    const freshnessState = computeFreshnessState(existing?.lastSuccessfulSyncUtc, now);
    const failureReason =
      error instanceof ProviderAccessDeniedError
        ? `PROVIDER_ACCESS_DENIED_${error.statusCode}`
        : error instanceof Error
          ? error.message
          : "NEWS_SYNC_FAILED";
    const usedBudget = error instanceof ProviderAccessDeniedError ? previousBudgetUsed : nextBudgetUsed;

    await upsertProviderStatus({
      provider: NEWS_PROVIDER,
      lastSuccessfulSyncUtc: existing?.lastSuccessfulSyncUtc ?? null,
      lastAttemptedSyncUtc: now,
      freshnessState,
      failureReason,
      budgetUsed: usedBudget,
      budgetLimit: env.NEWS_BUDGET_DAILY,
    });

    log.warn({ error }, "news sync failed");
    recordFileLog({
      category: "news",
      level: "warn",
      event: "news_sync_failed",
      message: "news sync failed",
      context: { freshnessState, failureReason, budgetUsed: usedBudget, error },
    });
  }
}

export function startNewsSync(log: LoggerLike): () => void {
  if (env.NODE_ENV === "test") {
    return () => undefined;
  }

  if (!env.NEWS_SYNC_ENABLED) {
    void syncNewsNow(log).catch((error) => {
      log.warn({ error }, "disabled news sync status update failed");
    });
    return () => undefined;
  }

  void syncNewsNow(log).catch((error) => {
    log.warn({ error }, "initial news sync run failed");
  });

  const timer = setInterval(() => {
    void syncNewsNow(log).catch((error) => {
      log.warn({ error }, "scheduled news sync run failed");
    });
  }, env.NEWS_SYNC_INTERVAL_MINUTES * 60_000);

  return () => clearInterval(timer);
}
