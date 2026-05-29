import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app";

const runDbTests = process.env.RUN_DB_TESTS === "true";

function uniqueId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

describe("backend app", () => {
  it("returns health status", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/health" });
    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.status).toBe("ok");
    expect(body.telemetry).toBeDefined();
    expect(body.telemetry.newsProvider.provider).toBe("FMP");
    expect(body.telemetry.newsProvider.tier).toBe("FREE");
    expect(["FRESH", "DEGRADED", "STALE", "DOWN"]).toContain(body.telemetry.newsProvider.freshnessState);
    await app.close();
  });

  it("returns provider status for news integrations", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/news/providers" });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(Array.isArray(body.items)).toBe(true);
    if (body.items.length > 0) {
      expect(body.items[0].provider).toBe("FMP");
      expect(body.items[0].tier).toBe("FREE");
    }

    await app.close();
  });

  (runDbTests ? it : it.skip)("supports admin approval and rollback workflow", async () => {
    const app = buildApp();
    const actionLabel = `Promote model ${uniqueId("xgb")}`;

    const submitResponse = await app.inject({
      method: "POST",
      url: "/admin/approvals/submit",
      payload: {
        actionType: "PROMOTE_MODEL",
        actionLabel,
        owner: "ml-lead",
        scope: "demo",
        requestedBy: "admin-operator",
        reason: "Promotion request with complete validation evidence.",
        strategyId: "daily-breakout-5-10",
        strategyVersion: "1.0.0",
      },
    });

    expect(submitResponse.statusCode).toBe(200);
    const submitBody = submitResponse.json();
    expect(submitBody.ok).toBe(true);
    expect(typeof submitBody.approval?.approvalId).toBe("string");

    const approvalId = submitBody.approval.approvalId;
    const approveResponse = await app.inject({
      method: "POST",
      url: `/admin/approvals/${approvalId}/approve`,
      payload: {
        actor: "admin",
        reason: "Validation gates are green and risk posture is stable.",
      },
    });

    expect(approveResponse.statusCode).toBe(200);
    const approveBody = approveResponse.json();
    expect(approveBody.ok).toBe(true);
    expect(approveBody.approval.state).toBe("APPROVED");

    const snapshotsResponse = await app.inject({
      method: "GET",
      url: "/admin/config-snapshots?strategyId=daily-breakout-5-10&strategyVersion=1.0.0&limit=1",
    });
    expect(snapshotsResponse.statusCode).toBe(200);

    const snapshotsBody = snapshotsResponse.json();
    if (snapshotsBody.items.length > 0) {
      const rollbackResponse = await app.inject({
        method: "POST",
        url: "/admin/config-snapshots/rollback",
        payload: {
          configId: snapshotsBody.items[0].id,
          actor: "admin",
          reason: "Regression controls require immediate rollback for safety.",
        },
      });

      expect(rollbackResponse.statusCode).toBe(200);
      expect(rollbackResponse.json().ok).toBe(true);
    }

    const auditResponse = await app.inject({
      method: "GET",
      url: "/admin/audit-log?limit=20",
    });

    expect(auditResponse.statusCode).toBe(200);
    expect(Array.isArray(auditResponse.json().items)).toBe(true);

    await app.close();
  });

  (runDbTests ? it : it.skip)("evaluates signal deterministically", async () => {
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

  (runDbTests ? it : it.skip)("evaluates portfolio plans with risk caps", async () => {
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

  (runDbTests ? it : it.skip)("returns portfolio summary and supports incident acknowledgement", async () => {
    const app = buildApp();

    const summaryResponse = await app.inject({
      method: "GET",
      url: "/portfolio/summary?maxOpenRisk=0.04&maxOpenTrades=6",
    });

    expect(summaryResponse.statusCode).toBe(200);
    const summaryBody = summaryResponse.json();
    expect(summaryBody.openRiskBudget).toBeDefined();
    expect(summaryBody.tradeSlots).toBeDefined();
    expect(Array.isArray(summaryBody.exposureBySymbol)).toBe(true);

    const incidentsResponse = await app.inject({
      method: "GET",
      url: "/incidents?limit=20",
    });

    expect(incidentsResponse.statusCode).toBe(200);
    const incidentsBody = incidentsResponse.json();
    expect(Array.isArray(incidentsBody.items)).toBe(true);

    if (incidentsBody.items.length > 0) {
      const acknowledgeResponse = await app.inject({
        method: "POST",
        url: `/incidents/${incidentsBody.items[0].incidentId}/acknowledge`,
        payload: {
          actor: "analyst",
          note: "Reviewed timeline and confirmed runbook handoff.",
        },
      });

      expect(acknowledgeResponse.statusCode).toBe(200);
      expect(acknowledgeResponse.json().ok).toBe(true);
    }

    await app.close();
  });
});
