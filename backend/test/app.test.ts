import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app";

describe("backend app", () => {
  it("returns health status", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/health" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.status).toBe("ok");
    expect(body.telemetry).toBeDefined();
    expect(body.telemetry.newsProvider).toBe("FMP");
    expect(body.telemetry.newsProviderTier).toBe("FREE");
    expect(["FRESH", "DEGRADED", "STALE", "DOWN"]).toContain(body.telemetry.newsFreshness);
    await app.close();
  });

  it("returns provider status for news integrations", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/news/providers" });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.count).toBe(1);
    expect(Array.isArray(body.items)).toBe(true);
    expect(body.items[0].provider).toBe("FMP");
    expect(body.items[0].tier).toBe("FREE");

    await app.close();
  });

  it("evaluates signal deterministically", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/signal",
      payload: {
        decisionId: "dec-1",
        strategyId: "daily-breakout-5-10",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        timeframe: "D1",
        barCloseTimeUtc: "2026-05-20T00:00:00.000Z",
        marketSnapshot: {
          symbol: "EURUSD",
          timeframe: "D1",
          barCloseTimeUtc: "2026-05-20T00:00:00.000Z",
          close1: 1.2,
          sma100_1: 1.1,
          sma200_1: 1.0,
          highestHigh55: 1.15,
          lowestLow55: 0.9,
          atr20_1: 0.01,
          volatility: 0.8,
          spreadPrice: 0.0002,
        },
        accountSnapshot: {
          accountId: "acct-1",
          openRisk: 0.01,
          openTrades: 1,
        },
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(["BUY", "SELL", "HOLD"]).toContain(body.action);
    expect(body.decisionId).toBe("dec-1");
    await app.close();
  });

  it("evaluates portfolio plans with risk caps", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/portfolio/evaluate",
      payload: {
        accountSnapshot: {
          accountId: "acct-1",
          openRisk: 0.01,
          openTrades: 1,
        },
        plans: [
          { decisionId: "d-1", strategyId: "s-1", symbol: "EURUSD", proposedRiskPct: 0.01 },
          { decisionId: "d-2", strategyId: "s-1", symbol: "GBPUSD", proposedRiskPct: 0.04 },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(Array.isArray(body.approvedPlans)).toBe(true);
    expect(Array.isArray(body.rejectedPlans)).toBe(true);
    await app.close();
  });
});
