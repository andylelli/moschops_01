import type { FastifyInstance } from "fastify";
import type { NewsEvent, NewsProviderStatus, Prisma } from "@prisma/client";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { NEWS_PROVIDER } from "../services/news-domain";
import { env } from "../utils/env";

type ActiveWindow = Prisma.NewsGuardWindowGetPayload<{ include: { newsEvent: true } }>;

const listQuerySchema = z.object({
  symbol: z.string().optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

export async function newsRoutes(app: FastifyInstance): Promise<void> {
  app.get("/news/upcoming", async (req, reply) => {
    const parsed = listQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const now = new Date();
    const symbol = parsed.data.symbol?.toUpperCase();

    let events: NewsEvent[] = [];

    try {
      events = await prismaClient().newsEvent.findMany({
        where: {
          scheduledAtUtc: { gte: now },
          ...(symbol
            ? {
                guardWindows: {
                  some: { symbolScope: symbol },
                },
              }
            : {}),
        },
        orderBy: { scheduledAtUtc: "asc" },
        take: parsed.data.limit,
      });
    } catch {
      events = [];
    }

    return {
      provider: NEWS_PROVIDER,
      count: events.length,
      items: events.map((event) => ({
        newsEventId: event.newsEventId,
        title: event.title,
        eventType: event.eventType,
        countryCode: event.countryCode,
        currencyCode: event.currencyCode,
        severity: event.severity,
        scheduledAtUtc: event.scheduledAtUtc.toISOString(),
        forecastValue: event.forecastValue,
        previousValue: event.previousValue,
        actualValue: event.actualValue,
        status: event.status,
      })),
    };
  });

  app.get("/news/active", async (req, reply) => {
    const parsed = listQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const now = new Date();
    const symbol = parsed.data.symbol?.toUpperCase();

    let windows: ActiveWindow[] = [];

    try {
      windows = await prismaClient().newsGuardWindow.findMany({
        where: {
          startsAtUtc: { lte: now },
          endsAtUtc: { gte: now },
          ...(symbol ? { symbolScope: symbol } : {}),
        },
        orderBy: [{ startsAtUtc: "asc" }],
        take: parsed.data.limit,
        include: {
          newsEvent: true,
        },
      });
    } catch {
      windows = [];
    }

    return {
      provider: NEWS_PROVIDER,
      count: windows.length,
      items: windows.map((window) => ({
        guardWindowId: window.guardWindowId,
        newsEventId: window.newsEventId,
        title: window.newsEvent.title,
        symbolScope: window.symbolScope,
        currencyScope: window.currencyScope,
        policyAction: window.policyAction,
        severity: window.severity,
        reasonCode: window.reasonCode,
        startsAtUtc: window.startsAtUtc.toISOString(),
        endsAtUtc: window.endsAtUtc.toISOString(),
      })),
    };
  });

  app.get("/news/providers", async () => {
    if (!env.NEWS_SYNC_ENABLED) {
      return {
        items: [
          {
            provider: NEWS_PROVIDER,
            tier: env.NEWS_PROVIDER_TIER,
            freshnessState: "DOWN",
            lastAttemptedSyncUtc: null,
            lastSuccessfulSyncUtc: null,
            failureReason: "NEWS_SYNC_DISABLED",
            budgetUsed: 0,
            budgetLimit: env.NEWS_BUDGET_DAILY,
          },
        ],
      };
    }

    let providers: NewsProviderStatus[] = [];

    try {
      providers = await prismaClient().newsProviderStatus.findMany({
        orderBy: { provider: "asc" },
      });
    } catch {
      providers = [];
    }

    return {
      items: providers.map((provider) => ({
        provider: provider.provider,
        tier: env.NEWS_PROVIDER_TIER,
        freshnessState: provider.freshnessState,
        lastAttemptedSyncUtc: provider.lastAttemptedSyncUtc.toISOString(),
        lastSuccessfulSyncUtc: provider.lastSuccessfulSyncUtc?.toISOString() ?? null,
        failureReason: provider.failureReason,
        budgetUsed: provider.budgetUsed,
        budgetLimit: provider.budgetLimit,
      })),
    };
  });
}
