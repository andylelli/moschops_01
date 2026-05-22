import { writeFile } from "node:fs/promises";
import path from "node:path";
import { isDeepStrictEqual } from "node:util";
import { buildApp } from "../app";

interface IdempotencyResult {
  name: string;
  status: "pass" | "fail";
  details: string;
}

function stableJson(value: unknown): string {
  return JSON.stringify(value);
}

function summarizeTopLevelDiff(left: unknown, right: unknown): string {
  if (!left || typeof left !== "object" || !right || typeof right !== "object") {
    return "non-object mismatch";
  }

  const leftObj = left as Record<string, unknown>;
  const rightObj = right as Record<string, unknown>;
  const keys = Array.from(new Set([...Object.keys(leftObj), ...Object.keys(rightObj)])).sort();
  const changed = keys.filter((key) => stableJson(leftObj[key]) !== stableJson(rightObj[key]));

  if (changed.length === 0) {
    return "json string mismatch with no top-level key differences";
  }

  const firstKey = changed[0];
  const leftValue = stableJson(leftObj[firstKey]);
  const rightValue = stableJson(rightObj[firstKey]);
  return `changedKeys:${changed.join(",")};${firstKey}:first=${leftValue};replay=${rightValue}`;
}

function assertEqual(name: string, left: unknown, right: unknown): IdempotencyResult {
  const same = isDeepStrictEqual(left, right);
  return {
    name,
    status: same ? "pass" : "fail",
    details: same ? "responses are replay-stable" : summarizeTopLevelDiff(left, right),
  };
}

async function main(): Promise<void> {
  const app = buildApp();
  const results: IdempotencyResult[] = [];
  const nowIso = new Date().toISOString();
  const suffix = `${Date.now()}`;

  try {
    await app.ready();

    const signalPayload = {
      decisionId: `idemp-signal-${suffix}`,
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
        close1: 1.101,
        sma100_1: 1.099,
        sma200_1: 1.095,
        highestHigh55: 1.102,
        lowestLow55: 1.085,
        atr20_1: 0.005,
        volatility: 0.01,
        spreadPrice: 0.0002,
      },
      accountSnapshot: {
        accountId: "acct-idemp-1",
        equity: 10000,
        balance: 10000,
        openRisk: 0.01,
        openTrades: 1,
        dailyLossPct: 0,
        weeklyLossPct: 0,
      },
    };

    const signalFirst = await app.inject({ method: "POST", url: "/signal", payload: signalPayload });
    const signalReplay = await app.inject({ method: "POST", url: "/signal", payload: signalPayload });

    results.push({
      name: "signal status check",
      status: signalFirst.statusCode === 200 && signalReplay.statusCode === 200 ? "pass" : "fail",
      details: `first=${signalFirst.statusCode}, replay=${signalReplay.statusCode}`,
    });

    results.push(assertEqual("signal response replay", signalFirst.json(), signalReplay.json()));

    const portfolioPayload = {
      accountSnapshot: {
        accountId: "acct-idemp-1",
        openRisk: 0.01,
        openTrades: 1,
        dailyLossPct: 0,
        weeklyLossPct: 0,
      },
      plans: [
        {
          decisionId: `idemp-plan-${suffix}`,
          strategyId: "daily-breakout-5-10",
          symbol: "EURUSD",
          proposedRiskPct: 0.01,
        },
      ],
      maxOpenRisk: 0.04,
      maxOpenTrades: 6,
    };

    const portfolioFirst = await app.inject({ method: "POST", url: "/portfolio/evaluate", payload: portfolioPayload });
    const portfolioReplay = await app.inject({ method: "POST", url: "/portfolio/evaluate", payload: portfolioPayload });

    results.push({
      name: "portfolio status check",
      status: portfolioFirst.statusCode === 200 && portfolioReplay.statusCode === 200 ? "pass" : "fail",
      details: `first=${portfolioFirst.statusCode}, replay=${portfolioReplay.statusCode}`,
    });

    results.push(assertEqual("portfolio response replay", portfolioFirst.json(), portfolioReplay.json()));

    const report = {
      generatedAtUtc: new Date().toISOString(),
      results,
      passCount: results.filter((result) => result.status === "pass").length,
      failCount: results.filter((result) => result.status === "fail").length,
    };

    await writeFile(path.resolve(process.cwd(), "idempotency_test_report.json"), JSON.stringify(report, null, 2), "utf8");

    for (const result of results) {
      console.log(`RESULT:${JSON.stringify(result)}`);
    }
  } finally {
    await app.close();
  }
}

void main();
