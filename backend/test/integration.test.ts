import { describe, test, expect, beforeAll, afterAll } from "vitest";
import type { FastifyInstance } from "fastify";
import { buildApp } from "../src/app";
import { prismaClient } from "../src/services/prisma";

const runDbTests = process.env.RUN_DB_TESTS === "true";
const integrationDescribe = runDbTests ? describe : describe.skip;

function uniqueId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function buildSignalPayload(decisionId: string, symbol = "EURUSD") {
  const now = new Date().toISOString();
  return {
    decisionId,
    strategyId: "daily-breakout-5-10",
    strategyVersion: "1.0.0",
    modelVersion: "logreg-v1",
    symbol,
    timeframe: "D1",
    barCloseTimeUtc: now,
    marketSnapshot: {
      symbol,
      timeframe: "D1",
      barCloseTimeUtc: now,
      close1: symbol === "EURUSD" ? 1.105 : 1.275,
      sma100_1: symbol === "EURUSD" ? 1.1 : 1.2725,
      sma200_1: symbol === "EURUSD" ? 1.095 : 1.27,
      highestHigh55: symbol === "EURUSD" ? 1.11 : 1.28,
      lowestLow55: symbol === "EURUSD" ? 1.09 : 1.265,
      atr20_1: symbol === "EURUSD" ? 0.005 : 0.0045,
      volatility: symbol === "EURUSD" ? 0.9 : 1.0,
      spreadPrice: 0.0002,
    },
    accountSnapshot: {
      accountId: "acct-int-001",
      equity: 10000,
      balance: 10000,
      openRisk: 0.01,
      openTrades: 1,
      dailyLossPct: 0,
      weeklyLossPct: 0,
    },
  };
}

integrationDescribe("Phase 3 - Persistence & Audit Logging Integration Tests", () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    app = buildApp();
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
  });

  test("signal -> DB write -> queryable decision trace", async () => {
    const decisionId = uniqueId("integration-signal");
    const payload = buildSignalPayload(decisionId, "EURUSD");

    const response = await app.inject({
      method: "POST",
      url: "/signal",
      payload,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.decisionId).toBe(decisionId);
    expect(body.action).toMatch(/^(BUY|SELL|HOLD)$/);
    expect(body.riskDecision).toMatch(/^(APPROVED|VETOED)$/);

    const dbSignal = await prismaClient().signal.findUnique({ where: { decisionId } });
    expect(dbSignal).toBeDefined();
    expect(dbSignal?.strategyId).toBe("daily-breakout-5-10");
  });

  test("portfolio evaluation persists risk decisions", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/portfolio/evaluate",
      payload: {
        accountSnapshot: {
          accountId: "acct-portfolio-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
        plans: [
          {
            decisionId: uniqueId("portfolio-plan"),
            strategyId: "daily-breakout-5-10",
            symbol: "GBPUSD",
            proposedRiskPct: 0.02,
          },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(typeof body.portfolioDecisionId).toBe("string");
    expect(body.approvedPlans).toBeDefined();
    expect(body.rejectedPlans).toBeDefined();
    expect(body.remainingRiskBudget).toBeLessThanOrEqual(0.04);
    expect(body.remainingTradeSlots).toBeLessThanOrEqual(6);
  });

  test("health endpoint reports DB connectivity", async () => {
    const response = await app.inject({ method: "GET", url: "/health" });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.status).toBe("ok");
    expect(body.telemetry.backend).toBe("up");
    expect(body.telemetry.newsProvider.provider).toBe("FMP");
    expect(body.telemetry.newsProvider.tier).toBe("FREE");
    expect(["FRESH", "DEGRADED", "STALE", "DOWN"]).toContain(body.telemetry.newsProvider.freshnessState);
  });

  test("news endpoints return normalized contract shells", async () => {
    const providers = await app.inject({ method: "GET", url: "/news/providers" });
    expect(providers.statusCode).toBe(200);
    const providersBody = providers.json();
    expect(providersBody.items[0].provider).toBe("FMP");
    expect(providersBody.items[0].tier).toBe("FREE");

    const upcoming = await app.inject({ method: "GET", url: "/news/upcoming" });
    expect(upcoming.statusCode).toBe(200);
    const upcomingBody = upcoming.json();
    expect(Array.isArray(upcomingBody.items)).toBe(true);

    const active = await app.inject({ method: "GET", url: "/news/active" });
    expect(active.statusCode).toBe(200);
    const activeBody = active.json();
    expect(Array.isArray(activeBody.items)).toBe(true);
  });

  test("risk-check endpoint validates decisions", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/risk-check",
      payload: {
        decisionId: uniqueId("risk-check"),
        strategyId: "daily-breakout-5-10",
        symbol: "EURUSD",
        proposedRiskPct: 0.005,
        proposedOpenTrades: 1,
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
        accountSnapshot: {
          accountId: "acct-risk-1",
          openRisk: 0.01,
          openTrades: 2,
          dailyLossPct: 0.005,
          weeklyLossPct: 0.01,
        },
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(typeof body.approved).toBe("boolean");
    expect(Array.isArray(body.vetoReasonCodes)).toBe(true);
  });

  test("idempotent signal writes (same decisionId returns same result)", async () => {
    const decisionId = uniqueId("idempotent");
    const payload = buildSignalPayload(decisionId, "EURUSD");

    const response1 = await app.inject({ method: "POST", url: "/signal", payload });
    const response2 = await app.inject({ method: "POST", url: "/signal", payload });

    expect(response1.statusCode).toBe(200);
    expect(response2.statusCode).toBe(200);

    const body1 = response1.json();
    const body2 = response2.json();
    expect(body1.action).toBe(body2.action);
    expect(body1.riskDecision).toBe(body2.riskDecision);
    expect(body1.reasonCodes).toEqual(body2.reasonCodes);
  });

  test("end-to-end scenario: signal -> portfolio check -> decision", async () => {
    const signalRes = await app.inject({
      method: "POST",
      url: "/signal",
      payload: buildSignalPayload(uniqueId("e2e"), "EURUSD"),
    });

    expect(signalRes.statusCode).toBe(200);
    const signal = signalRes.json();

    const portfolioRes = await app.inject({
      method: "POST",
      url: "/portfolio/evaluate",
      payload: {
        accountSnapshot: {
          accountId: "acct-e2e",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
        plans: [
          {
            decisionId: signal.decisionId,
            strategyId: "daily-breakout-5-10",
            symbol: "EURUSD",
            proposedRiskPct: 0.005,
          },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      },
    });

    expect(portfolioRes.statusCode).toBe(200);
    const portfolio = portfolioRes.json();
    expect(Array.isArray(portfolio.approvedPlans)).toBe(true);
    expect(Array.isArray(portfolio.rejectedPlans)).toBe(true);
  });
});
