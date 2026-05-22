import { writeFile } from "node:fs/promises";
import path from "node:path";

interface ProbeResult {
  scenario: string;
  aiScore: number;
  expectedBucket: "FULL" | "HALF" | "SKIP";
  actualBucket: string;
  expectedAction: "BUY" | "HOLD";
  actualAction: string;
  status: "pass" | "fail";
}

async function main(): Promise<void> {
  process.env.NODE_ENV = "test";
  process.env.NEWS_SYNC_ENABLED = "true";

  const [{ buildApp }, { prismaClient }, { NEWS_PROVIDER }, { env }] = await Promise.all([
    import("../app"),
    import("../services/prisma"),
    import("../services/news-domain"),
    import("../utils/env"),
  ]);

  const app = buildApp();
  const db = prismaClient();
  const originalStatus = await db.newsProviderStatus.findUnique({ where: { provider: NEWS_PROVIDER } });

  try {
    await app.ready();

    // Keep provider in fresh state so threshold behavior is not masked by stale/down veto.
    await db.newsProviderStatus.upsert({
      where: { provider: NEWS_PROVIDER },
      create: {
        provider: NEWS_PROVIDER,
        lastAttemptedSyncUtc: new Date(),
        lastSuccessfulSyncUtc: new Date(),
        freshnessState: "FRESH",
        failureReason: null,
        budgetUsed: 1,
        budgetLimit: env.NEWS_BUDGET_DAILY,
      },
      update: {
        lastAttemptedSyncUtc: new Date(),
        lastSuccessfulSyncUtc: new Date(),
        freshnessState: "FRESH",
        failureReason: null,
        budgetUsed: 1,
        budgetLimit: env.NEWS_BUDGET_DAILY,
      },
    });

    const nowBase = new Date();
    const suffix = Date.now().toString();

    const scenarios = [
      { scenario: "full-size", aiScore: 0.7, expectedBucket: "FULL" as const, expectedAction: "BUY" as const },
      { scenario: "half-size", aiScore: 0.6, expectedBucket: "HALF" as const, expectedAction: "BUY" as const },
      { scenario: "skip", aiScore: 0.5, expectedBucket: "SKIP" as const, expectedAction: "HOLD" as const },
    ];

    const results: ProbeResult[] = [];

    for (const [index, item] of scenarios.entries()) {
      const barCloseTimeUtc = new Date(nowBase.getTime() + index * 60_000).toISOString();
      const response = await app.inject({
        method: "POST",
        url: "/signal",
        payload: {
          decisionId: `threshold-${item.scenario}-${suffix}`,
          strategyId: "daily-breakout-5-10",
          strategyVersion: "1.0.0",
          modelVersion: "logreg-2026-05-20",
          symbol: "EURUSD",
          timeframe: "H1",
          barCloseTimeUtc,
          aiScore: item.aiScore,
          marketSnapshot: {
            symbol: "EURUSD",
            timeframe: "H1",
            barCloseTimeUtc,
            close1: 1.13,
            sma100_1: 1.1,
            sma200_1: 1.09,
            highestHigh55: 1.12,
            lowestLow55: 1.05,
            atr20_1: 0.005,
            volatility: 0.01,
            spreadPrice: 0.0002,
          },
          accountSnapshot: {
            accountId: "acct-threshold-1",
            equity: 10000,
            balance: 10000,
            openRisk: 0.01,
            openTrades: 1,
            dailyLossPct: 0,
            weeklyLossPct: 0,
          },
        },
      });

      const body = response.json() as { sizeBucket?: string; action?: string };
      const result: ProbeResult = {
        scenario: item.scenario,
        aiScore: item.aiScore,
        expectedBucket: item.expectedBucket,
        actualBucket: body.sizeBucket ?? "UNKNOWN",
        expectedAction: item.expectedAction,
        actualAction: body.action ?? "UNKNOWN",
        status:
          response.statusCode === 200 && body.sizeBucket === item.expectedBucket && body.action === item.expectedAction
            ? "pass"
            : "fail",
      };
      results.push(result);
      console.log(`RESULT:${JSON.stringify(result)}`);
    }

    const report = {
      generatedAtUtc: new Date().toISOString(),
      results,
      passCount: results.filter((result) => result.status === "pass").length,
      failCount: results.filter((result) => result.status === "fail").length,
    };

    await writeFile(path.resolve(process.cwd(), "inference_threshold_report.json"), JSON.stringify(report, null, 2), "utf8");
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
    }

    await app.close();
  }
}

void main();
