import { writeFile } from "node:fs/promises";
import path from "node:path";
import type { NewsProviderStatus } from "@prisma/client";

interface ProbeResult {
  state: "FRESH" | "DEGRADED" | "STALE" | "DOWN";
  expected: string;
  healthState: string;
  providerState: string;
  status: "pass" | "fail";
  lastSuccessfulSyncUtc: string | null;
}

async function main(): Promise<void> {
  process.env.NODE_ENV = "test";
  process.env.NEWS_SYNC_ENABLED = "true";

  const [{ buildApp }, { prismaClient }, { NEWS_PROVIDER, computeFreshnessState }, { env }] = await Promise.all([
    import("../app"),
    import("../services/prisma"),
    import("../services/news-domain"),
    import("../utils/env"),
  ]);

  const app = buildApp();
  const db = prismaClient();
  const now = new Date();
  const originalStatus = await db.newsProviderStatus.findUnique({ where: { provider: NEWS_PROVIDER } });

  try {
    await app.ready();

    const scenarios: Array<{ state: "FRESH" | "DEGRADED" | "STALE" | "DOWN"; lastSuccessful: Date | null }> = [
      { state: "FRESH", lastSuccessful: new Date(now.getTime() - 1 * 60_000) },
      { state: "DEGRADED", lastSuccessful: new Date(now.getTime() - (env.NEWS_DEGRADED_MINUTES + 1) * 60_000) },
      { state: "STALE", lastSuccessful: new Date(now.getTime() - (env.NEWS_STALE_MINUTES + 1) * 60_000) },
      { state: "DOWN", lastSuccessful: null },
    ];

    const results: ProbeResult[] = [];

    for (const scenario of scenarios) {
      const expected = computeFreshnessState(scenario.lastSuccessful, now);

      await db.newsProviderStatus.upsert({
        where: { provider: NEWS_PROVIDER },
        create: {
          provider: NEWS_PROVIDER,
          lastAttemptedSyncUtc: now,
          lastSuccessfulSyncUtc: scenario.lastSuccessful,
          freshnessState: expected,
          failureReason: scenario.lastSuccessful ? null : "TEST_DOWN",
          budgetUsed: 1,
          budgetLimit: env.NEWS_BUDGET_DAILY,
        },
        update: {
          lastAttemptedSyncUtc: now,
          lastSuccessfulSyncUtc: scenario.lastSuccessful,
          freshnessState: expected,
          failureReason: scenario.lastSuccessful ? null : "TEST_DOWN",
          budgetUsed: 1,
          budgetLimit: env.NEWS_BUDGET_DAILY,
        },
      });

      const healthResponse = await app.inject({ method: "GET", url: "/health" });
      const providersResponse = await app.inject({ method: "GET", url: "/news/providers" });

      const healthBody = healthResponse.json() as {
        telemetry?: {
          newsProvider?: {
            freshnessState?: string;
          };
        };
      };
      const providersBody = providersResponse.json() as {
        items?: Array<{
          freshnessState?: string;
        }>;
      };

      const healthState = healthBody.telemetry?.newsProvider?.freshnessState ?? "UNKNOWN";
      const providerState = providersBody.items?.[0]?.freshnessState ?? "UNKNOWN";
      const ok = healthState === expected && providerState === expected;

      results.push({
        state: scenario.state,
        expected,
        healthState,
        providerState,
        status: ok ? "pass" : "fail",
        lastSuccessfulSyncUtc: scenario.lastSuccessful?.toISOString() ?? null,
      });

      console.log(
        `RESULT:${JSON.stringify({
          state: scenario.state,
          expected,
          healthState,
          providerState,
          status: ok ? "pass" : "fail",
        })}`,
      );
    }

    const report = {
      generatedAtUtc: new Date().toISOString(),
      thresholds: {
        degradedMinutes: env.NEWS_DEGRADED_MINUTES,
        staleMinutes: env.NEWS_STALE_MINUTES,
      },
      nowUtc: now.toISOString(),
      results,
      passCount: results.filter((result) => result.status === "pass").length,
      failCount: results.filter((result) => result.status === "fail").length,
    };

    await writeFile(path.resolve(process.cwd(), "freshness_transition_report.json"), JSON.stringify(report, null, 2), "utf8");
  } finally {
    if (originalStatus) {
      await db.newsProviderStatus.upsert({
        where: { provider: originalStatus.provider },
        create: originalStatus,
        update: {
          lastAttemptedSyncUtc: originalStatus.lastAttemptedSyncUtc,
          lastSuccessfulSyncUtc: originalStatus.lastSuccessfulSyncUtc,
          freshnessState: originalStatus.freshnessState,
          failureReason: originalStatus.failureReason,
          budgetUsed: originalStatus.budgetUsed,
          budgetLimit: originalStatus.budgetLimit,
        },
      });
    } else {
      await db.newsProviderStatus.deleteMany({ where: { provider: NEWS_PROVIDER } });
    }

    await app.close();
  }
}

void main();
