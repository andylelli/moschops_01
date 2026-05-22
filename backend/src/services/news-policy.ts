import type { PrismaClient, Prisma } from "@prisma/client";
import { prismaClient } from "./prisma";
import { NEWS_PROVIDER, NewsFreshnessState, computeFreshnessState } from "./news-domain";

export interface NewsPolicyDecision {
  approved: boolean;
  policyAction: "ALLOW" | "REDUCE" | "BLOCK_NEW";
  reasonCodes: string[];
  freshnessState: NewsFreshnessState;
  provider: string;
  newsEventId?: string;
}

type DbLike = PrismaClient | Prisma.TransactionClient;

function actionPriority(policyAction: string): number {
  if (policyAction === "BLOCK_NEW") {
    return 3;
  }

  if (policyAction === "REDUCE") {
    return 2;
  }

  return 1;
}

export async function evaluateNewsPolicy(input: {
  symbol: string;
  isEntryAction: boolean;
  now?: Date;
  db?: DbLike;
}): Promise<NewsPolicyDecision> {
  const db = input.db ?? prismaClient();
  const now = input.now ?? new Date();

  try {
    const providerStatus = await db.newsProviderStatus.findUnique({
      where: { provider: NEWS_PROVIDER },
    });

    const freshnessState = computeFreshnessState(providerStatus?.lastSuccessfulSyncUtc, now);

    if (!input.isEntryAction) {
      return {
        approved: true,
        policyAction: "ALLOW",
        reasonCodes: [],
        freshnessState,
        provider: NEWS_PROVIDER,
      };
    }

    if (freshnessState === "STALE" || freshnessState === "DOWN") {
      return {
        approved: false,
        policyAction: "BLOCK_NEW",
        reasonCodes: ["NEWS_PROVIDER_STALE"],
        freshnessState,
        provider: NEWS_PROVIDER,
      };
    }

    const activeWindows = await db.newsGuardWindow.findMany({
      where: {
        symbolScope: input.symbol.toUpperCase(),
        startsAtUtc: { lte: now },
        endsAtUtc: { gte: now },
      },
      include: { newsEvent: true },
    });

    if (activeWindows.length === 0) {
      return {
        approved: true,
        policyAction: "ALLOW",
        reasonCodes: [],
        freshnessState,
        provider: NEWS_PROVIDER,
      };
    }

    const selected = activeWindows.sort((a, b) => actionPriority(b.policyAction) - actionPriority(a.policyAction))[0];

    if (selected.policyAction === "BLOCK_NEW") {
      return {
        approved: false,
        policyAction: "BLOCK_NEW",
        reasonCodes: ["NEWS_BLOCK_HIGH_IMPACT"],
        freshnessState,
        provider: NEWS_PROVIDER,
        newsEventId: selected.newsEventId,
      };
    }

    if (selected.policyAction === "REDUCE") {
      return {
        approved: true,
        policyAction: "REDUCE",
        reasonCodes: ["NEWS_REDUCE_MEDIUM_IMPACT"],
        freshnessState,
        provider: NEWS_PROVIDER,
        newsEventId: selected.newsEventId,
      };
    }

    return {
      approved: true,
      policyAction: "ALLOW",
      reasonCodes: [],
      freshnessState,
      provider: NEWS_PROVIDER,
      newsEventId: selected.newsEventId,
    };
  } catch {
    return {
      approved: false,
      policyAction: "BLOCK_NEW",
      reasonCodes: ["NEWS_PROVIDER_STALE"],
      freshnessState: "DOWN",
      provider: NEWS_PROVIDER,
    };
  }
}
