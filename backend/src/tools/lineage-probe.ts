import { writeFile } from "node:fs/promises";
import path from "node:path";
import { buildApp } from "../app";
import { prismaClient } from "../services/prisma";

interface LineageSqlRow {
  decisionId: string;
  signalId: string;
  strategyId: string;
  strategyVersion: string;
  modelVersion: string | null;
  tradeId: string | null;
  tradeStatus: string | null;
  closeReason: string | null;
}

interface ProbeResult {
  name: string;
  status: "pass" | "fail";
  details: string;
}

async function main(): Promise<void> {
  const app = buildApp();
  const results: ProbeResult[] = [];
  const nowIso = new Date().toISOString();
  const suffix = Date.now().toString();

  try {
    await app.ready();

    const decisionId = `lineage-${suffix}`;
    const tradeId = `lineage-trade-${suffix}`;

    const signalResponse = await app.inject({
      method: "POST",
      url: "/signal",
      payload: {
        decisionId,
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
          accountId: "acct-lineage-1",
          equity: 10000,
          balance: 10000,
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
      },
    });

    const signalBody = signalResponse.json() as { decisionId?: string; signalId?: string };

    results.push({
      name: "signal persisted",
      status: signalResponse.statusCode === 200 ? "pass" : "fail",
      details: `status=${signalResponse.statusCode}`,
    });

    const logTradeResponse = await app.inject({
      method: "POST",
      url: "/log-trade",
      payload: {
        tradeId,
        decisionId,
        signalId: signalBody.signalId,
        strategyId: "daily-breakout-5-10",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        side: "BUY",
        volume: 0.1,
        entryPrice: 1.13,
        status: "CLOSED",
        closeReason: "LINEAGE_PROBE_CLOSE",
      },
    });

    results.push({
      name: "trade persisted",
      status: logTradeResponse.statusCode === 200 ? "pass" : "fail",
      details: `status=${logTradeResponse.statusCode}`,
    });

    const rows = await prismaClient().$queryRaw<LineageSqlRow[]>`
      SELECT
        s."decisionId" AS "decisionId",
        s."signalId" AS "signalId",
        s."strategyId" AS "strategyId",
        s."strategyVersion" AS "strategyVersion",
        s."modelVersion" AS "modelVersion",
        t."tradeId" AS "tradeId",
        t."status" AS "tradeStatus",
        t."closeReason" AS "closeReason"
      FROM "Signal" s
      LEFT JOIN "Trade" t ON t."decisionId" = s."decisionId"
      WHERE s."decisionId" = ${decisionId}
      ORDER BY t."updatedAt" DESC
      LIMIT 1
    `;

    const chain = rows[0] ?? null;
    const chainOk =
      chain !== null &&
      chain.decisionId === decisionId &&
      typeof chain.signalId === "string" &&
      chain.strategyId === "daily-breakout-5-10" &&
      chain.strategyVersion === "1.0.0" &&
      chain.tradeId === tradeId;

    results.push({
      name: "lineage sql chain",
      status: chainOk ? "pass" : "fail",
      details: chainOk ? "signal->trade chain query returned expected IDs and versions" : "lineage query missing expected chain",
    });

    const report = {
      generatedAtUtc: new Date().toISOString(),
      decisionId,
      tradeId,
      signalResponseStatus: signalResponse.statusCode,
      logTradeResponseStatus: logTradeResponse.statusCode,
      sqlChainRow: chain,
      results,
      passCount: results.filter((result) => result.status === "pass").length,
      failCount: results.filter((result) => result.status === "fail").length,
    };

    await writeFile(path.resolve(process.cwd(), "lineage_test_report.json"), JSON.stringify(report, null, 2), "utf8");

    for (const result of results) {
      console.log(`RESULT:${JSON.stringify(result)}`);
    }
  } finally {
    await app.close();
  }
}

void main();
