import { prismaClient } from "./prisma";

export const NEWS_PROVIDER = "FMP";
export const NEWS_PROVIDER_TIER = "FREE";

export type NewsProviderSnapshot = {
  provider: string;
  tier: string;
  freshnessState: "FRESH" | "DEGRADED" | "STALE" | "DOWN";
  lastSuccessfulSyncUtc: string | null;
  lastAttemptedSyncUtc: string | null;
  failureReason: string | null;
};

function normalizeFreshnessState(value: string | null | undefined): NewsProviderSnapshot["freshnessState"] {
  if (value === "FRESH" || value === "DEGRADED" || value === "STALE" || value === "DOWN") {
    return value;
  }

  return "DOWN";
}

function toIsoOrNull(value: Date | null | undefined): string | null {
  return value ? value.toISOString() : null;
}

export async function getNewsProviderSnapshot(): Promise<NewsProviderSnapshot> {
  try {
    const status = await prismaClient().newsProviderStatus.findUnique({
      where: { provider: NEWS_PROVIDER },
    });

    return {
      provider: NEWS_PROVIDER,
      tier: NEWS_PROVIDER_TIER,
      freshnessState: normalizeFreshnessState(status?.freshnessState),
      lastSuccessfulSyncUtc: toIsoOrNull(status?.lastSuccessfulSyncUtc),
      lastAttemptedSyncUtc: toIsoOrNull(status?.lastAttemptedSyncUtc),
      failureReason: status?.failureReason ?? null,
    };
  } catch {
    return {
      provider: NEWS_PROVIDER,
      tier: NEWS_PROVIDER_TIER,
      freshnessState: "DOWN",
      lastSuccessfulSyncUtc: null,
      lastAttemptedSyncUtc: null,
      failureReason: "NEWS_STATUS_UNAVAILABLE",
    };
  }
}

export async function listUpcomingNews(limit = 50): Promise<unknown[]> {
  try {
    return await prismaClient().newsEvent.findMany({
      where: { scheduledAtUtc: { gte: new Date() } },
      orderBy: { scheduledAtUtc: "asc" },
      take: limit,
    });
  } catch {
    return [];
  }
}

export async function listActiveGuardWindows(at = new Date()): Promise<unknown[]> {
  try {
    return await prismaClient().newsGuardWindow.findMany({
      where: {
        startsAtUtc: { lte: at },
        endsAtUtc: { gte: at },
      },
      include: {
        newsEvent: {
          select: {
            newsEventId: true,
            provider: true,
            title: true,
            currencyCode: true,
            severity: true,
            scheduledAtUtc: true,
          },
        },
      },
      orderBy: { startsAtUtc: "asc" },
      take: 100,
    });
  } catch {
    return [];
  }
}