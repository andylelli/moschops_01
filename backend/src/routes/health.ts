import type { FastifyInstance } from "fastify";
import type { NewsProviderStatus } from "@prisma/client";
import { prismaClient } from "../services/prisma";
import { getModelLoaderStatus } from "../services/model-inference";
import { NEWS_PROVIDER } from "../services/news-domain";
import { env } from "../utils/env";

export async function healthRoutes(app: FastifyInstance): Promise<void> {
  app.get("/health", async () => {
    const shouldProbeDatabase = env.NODE_ENV !== "test" || process.env.RUN_DB_TESTS === "true";

    let db = "up";
    if (!shouldProbeDatabase) {
      db = "down";
    } else {
      try {
        await prismaClient().$queryRaw`SELECT 1`;
      } catch {
        db = "down";
      }
    }

    const modelStatus = getModelLoaderStatus();
    let providerStatus: NewsProviderStatus | null = null;

    if (shouldProbeDatabase) {
      try {
        providerStatus = await prismaClient().newsProviderStatus.findUnique({
          where: { provider: NEWS_PROVIDER },
        });
      } catch {
        providerStatus = null;
      }
    } else {
      providerStatus = null;
    }

    return {
      status: "ok",
      service: "moschops-backend",
      timestamp: new Date().toISOString(),
      telemetry: {
        backend: "up",
        database: db,
        modelLoader: modelStatus.state,
        modelReason: modelStatus.reason,
        newsProvider: {
          provider: NEWS_PROVIDER,
          tier: env.NEWS_PROVIDER_TIER,
          freshnessState: providerStatus?.freshnessState ?? "DOWN",
          lastAttemptedSyncUtc: providerStatus?.lastAttemptedSyncUtc?.toISOString() ?? null,
          lastSuccessfulSyncUtc: providerStatus?.lastSuccessfulSyncUtc?.toISOString() ?? null,
          failureReason: providerStatus?.failureReason ?? (env.NEWS_SYNC_ENABLED ? "NEWS_PROVIDER_UNINITIALIZED" : "NEWS_SYNC_DISABLED"),
          budgetUsed: providerStatus?.budgetUsed ?? 0,
          budgetLimit: providerStatus?.budgetLimit ?? null,
        },
      },
    };
  });
}
