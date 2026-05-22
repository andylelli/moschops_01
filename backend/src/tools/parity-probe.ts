import { writeFile } from "node:fs/promises";
import path from "node:path";

interface ProbeResult {
  name: string;
  status: "pass" | "fail";
  details: string;
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
  const now = new Date();
  const suffix = Date.now().toString();
  const originalStatus = await db.newsProviderStatus.findUnique({ where: { provider: NEWS_PROVIDER } });

  try {
    await app.ready();

    // Force stale/down decision path for deterministic parity checks.
    await db.newsProviderStatus.upsert({
      where: { provider: NEWS_PROVIDER },
      create: {
        provider: NEWS_PROVIDER,
        lastAttemptedSyncUtc: now,
        lastSuccessfulSyncUtc: null,
        freshnessState: "DOWN",
        failureReason: "PARITY_PROBE_FORCED_DOWN",
        budgetUsed: 0,
        budgetLimit: env.NEWS_BUDGET_DAILY,
      },
      update: {
        lastAttemptedSyncUtc: now,
        lastSuccessfulSyncUtc: null,
        freshnessState: "DOWN",
        failureReason: "PARITY_PROBE_FORCED_DOWN",
        budgetUsed: 0,
        budgetLimit: env.NEWS_BUDGET_DAILY,
      },
    });

    const nowIso = new Date().toISOString();
    const signalDecisionId = `parity-signal-${suffix}`;
    const riskDecisionId = `parity-risk-${suffix}`;
    const planDecisionId = `parity-plan-${suffix}`;

    const signalRes = await app.inject({
      method: "POST",
      url: "/signal",
      payload: {
        decisionId: signalDecisionId,
        strategyId: "daily-breakout-5-10",
        strategyVersion: "1.0.0",
        modelVersion: "logreg-2026-05-20",
        symbol: "EURUSD",
        timeframe: "H1",
        barCloseTimeUtc: nowIso,
        marketSnapshot: {
          symbol: "EURUSD",
          timeframe: "H1",
          barCloseTimeUtc: nowIso,
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
          accountId: "acct-parity-1",
          equity: 10000,
          balance: 10000,
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
      },
    });

    const riskRes = await app.inject({
      method: "POST",
      url: "/risk-check",
      payload: {
        decisionId: riskDecisionId,
        strategyId: "daily-breakout-5-10",
        symbol: "EURUSD",
        proposedRiskPct: 0.01,
        proposedOpenTrades: 1,
        accountSnapshot: {
          accountId: "acct-parity-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
      },
    });

    const portfolioRes = await app.inject({
      method: "POST",
      url: "/portfolio/evaluate",
      payload: {
        accountSnapshot: {
          accountId: "acct-parity-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
        plans: [
          {
            decisionId: planDecisionId,
            strategyId: "daily-breakout-5-10",
            symbol: "EURUSD",
            proposedRiskPct: 0.01,
          },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      },
    });

    const signalBody = signalRes.json() as { action?: string; riskDecision?: string; reasonCodes?: string[] };
    const riskBody = riskRes.json() as { approved?: boolean; vetoReasonCodes?: string[] };
    const portfolioBody = portfolioRes.json() as {
      approvedPlans?: string[];
      rejectedPlans?: Array<{ decisionId: string; reasonCodes: string[] }>;
    };

    const signalBlocked = signalBody.riskDecision === "VETOED" && signalBody.action === "HOLD";
    const riskBlocked = riskBody.approved === false;
    const portfolioBlocked =
      Array.isArray(portfolioBody.approvedPlans) &&
      portfolioBody.approvedPlans.length === 0 &&
      Array.isArray(portfolioBody.rejectedPlans) &&
      portfolioBody.rejectedPlans.some((plan) => plan.decisionId === planDecisionId);

    const signalReason = Array.isArray(signalBody.reasonCodes) && signalBody.reasonCodes.includes("NEWS_PROVIDER_STALE");
    const riskReason = Array.isArray(riskBody.vetoReasonCodes) && riskBody.vetoReasonCodes.includes("NEWS_PROVIDER_STALE");
    const portfolioReason =
      Array.isArray(portfolioBody.rejectedPlans) &&
      portfolioBody.rejectedPlans.some(
        (plan) => plan.decisionId === planDecisionId && Array.isArray(plan.reasonCodes) && plan.reasonCodes.includes("NEWS_PROVIDER_STALE"),
      );

    const results: ProbeResult[] = [
      {
        name: "signal blocked by news",
        status: signalBlocked ? "pass" : "fail",
        details: `status=${signalRes.statusCode}`,
      },
      {
        name: "risk-check blocked by news",
        status: riskBlocked ? "pass" : "fail",
        details: `status=${riskRes.statusCode}`,
      },
      {
        name: "portfolio blocked by news",
        status: portfolioBlocked ? "pass" : "fail",
        details: `status=${portfolioRes.statusCode}`,
      },
      {
        name: "reason code parity",
        status: signalReason && riskReason && portfolioReason ? "pass" : "fail",
        details: "expected NEWS_PROVIDER_STALE across all endpoints",
      },
    ];

    const report = {
      generatedAtUtc: new Date().toISOString(),
      forcedFreshnessState: "DOWN",
      signalResponse: signalBody,
      riskResponse: riskBody,
      portfolioResponse: portfolioBody,
      results,
      passCount: results.filter((result) => result.status === "pass").length,
      failCount: results.filter((result) => result.status === "fail").length,
    };

    await writeFile(path.resolve(process.cwd(), "parity_test_report.json"), JSON.stringify(report, null, 2), "utf8");

    for (const result of results) {
      console.log(`RESULT:${JSON.stringify(result)}`);
    }
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
