import { writeFile } from "node:fs/promises";
import path from "node:path";
import { buildApp } from "../app";
import { env } from "../utils/env";

interface ProbeResult {
  source: "backend" | "fmp";
  name: string;
  status: number;
  ok: boolean;
  summary: string;
}

function summarizeBody(body: unknown): string {
  if (!body || typeof body !== "object") {
    return "body";
  }

  const value = body as Record<string, unknown>;

  if (value.error && typeof value.error === "object" && value.error !== null) {
    const err = value.error as Record<string, unknown>;
    if (typeof err.code === "string") {
      return `error:${err.code}`;
    }
  }

  if (typeof value.count === "number") {
    return `count:${value.count}`;
  }

  if (typeof value.ok === "boolean") {
    return `ok:${value.ok}`;
  }

  if (typeof value.status === "string") {
    return `status:${value.status}`;
  }

  if (typeof value.action === "string") {
    return `action:${value.action}`;
  }

  if (typeof value.approved === "boolean") {
    return `approved:${value.approved}`;
  }

  if (typeof value.portfolioDecisionId === "string") {
    return "portfolioDecisionId";
  }

  if (Array.isArray(value.items)) {
    return `items:${value.items.length}`;
  }

  return "response";
}

async function backendTest(
  app: ReturnType<typeof buildApp>,
  name: string,
  method: "GET" | "POST",
  url: string,
  payload?: unknown,
): Promise<ProbeResult> {
  const response = (await app.inject({
    method,
    url,
    ...(payload === undefined ? {} : { payload: payload as Record<string, unknown> }),
  })) as unknown as {
    statusCode: number;
    body: string;
    json: () => unknown;
  };

  let summary = response.body.slice(0, 120);
  try {
    summary = summarizeBody(response.json());
  } catch {
    // keep body summary fallback
  }

  return {
    source: "backend",
    name,
    status: response.statusCode,
    ok: response.statusCode >= 200 && response.statusCode < 300,
    summary,
  };
}

async function fmpTest(name: string, url: string, useHeader: boolean): Promise<ProbeResult> {
  const headers: Record<string, string> = useHeader ? { apikey: env.FMP_API_KEY ?? "" } : {};
  const response = await fetch(url, { headers });

  let summary = "body:empty";
  const text = await response.text();
  if (text) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (Array.isArray(parsed)) {
        summary = `count:${parsed.length}`;
      } else if (parsed && typeof parsed === "object") {
        const objectValue = parsed as Record<string, unknown>;
        if (typeof objectValue.error === "string") {
          summary = `error:${objectValue.error}`;
        } else if (typeof objectValue.Error === "string") {
          summary = `error:${objectValue.Error}`;
        } else {
          summary = "json:object";
        }
      }
    } catch {
      summary = `text:${text.slice(0, 120)}`;
    }
  }

  return {
    source: "fmp",
    name,
    status: response.status,
    ok: response.ok,
    summary,
  };
}

async function main(): Promise<void> {
  const app = buildApp();
  const results: ProbeResult[] = [];
  const nowIso = new Date().toISOString();
  const suffix = Date.now().toString();

  try {
    await app.ready();

    results.push(await backendTest(app, "GET /health", "GET", "/health"));
    results.push(await backendTest(app, "GET /news/providers", "GET", "/news/providers"));
    results.push(await backendTest(app, "GET /news/active?limit=5", "GET", "/news/active?limit=5"));
    results.push(await backendTest(app, "GET /news/upcoming?limit=5", "GET", "/news/upcoming?limit=5"));

    results.push(
      await backendTest(app, "POST /trades/open", "POST", "/trades/open", {
        accountId: "acct-1",
        strategyId: "daily-breakout",
        symbol: "EURUSD",
        capturedAtUtc: nowIso,
        payload: { positions: [] },
      }),
    );
    results.push(await backendTest(app, "GET /trades/open", "GET", "/trades/open"));

    results.push(await backendTest(app, "GET /model-version", "GET", "/model-version"));
    results.push(await backendTest(app, "GET /performance", "GET", "/performance"));

    results.push(
      await backendTest(app, "POST /log-signal", "POST", "/log-signal", {
        decisionId: `decision-log-${suffix}`,
        signalId: `signal-log-${suffix}`,
        strategyId: "daily-breakout",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        timeframe: "H1",
        action: "HOLD",
        barCloseTimeUtc: nowIso,
        evaluatedAtUtc: nowIso,
        payload: { source: "api-test" },
      }),
    );

    results.push(
      await backendTest(app, "POST /log-rejected-signal", "POST", "/log-rejected-signal", {
        decisionId: `decision-rej-${suffix}`,
        signalId: `signal-rej-${suffix}`,
        strategyId: "daily-breakout",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        timeframe: "H1",
        reasonCode: "TEST_REJECT",
        payload: { source: "api-test" },
      }),
    );

    results.push(
      await backendTest(app, "POST /log-trade", "POST", "/log-trade", {
        tradeId: `trade-${suffix}`,
        decisionId: `decision-log-${suffix}`,
        signalId: `signal-log-${suffix}`,
        strategyId: "daily-breakout",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        side: "BUY",
        volume: 0.1,
        entryPrice: 1.1,
        status: "OPEN",
      }),
    );

    results.push(
      await backendTest(app, "POST /risk-check", "POST", "/risk-check", {
        decisionId: `risk-${suffix}`,
        strategyId: "daily-breakout",
        symbol: "EURUSD",
        proposedRiskPct: 0.01,
        proposedOpenTrades: 1,
        accountSnapshot: {
          accountId: "acct-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
      }),
    );

    results.push(
      await backendTest(app, "POST /portfolio/evaluate", "POST", "/portfolio/evaluate", {
        accountSnapshot: {
          accountId: "acct-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
        plans: [
          {
            decisionId: `plan-${suffix}`,
            strategyId: "daily-breakout",
            symbol: "EURUSD",
            proposedRiskPct: 0.01,
          },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      }),
    );

    results.push(
      await backendTest(app, "POST /signal", "POST", "/signal", {
        decisionId: `signal-${suffix}`,
        strategyId: "daily-breakout",
        strategyVersion: "1.0.0",
        modelVersion: "test-model",
        symbol: "EURUSD",
        timeframe: "H1",
        barCloseTimeUtc: nowIso,
        marketSnapshot: {
          symbol: "EURUSD",
          timeframe: "H1",
          barCloseTimeUtc: nowIso,
          close1: 1.1,
          sma100_1: 1.09,
          sma200_1: 1.08,
          highestHigh55: 1.12,
          lowestLow55: 1.03,
          atr20_1: 0.005,
          volatility: 0.01,
          spreadPrice: 0.0002,
          open0: 1.095,
          close1Prev: 1.097,
        },
        accountSnapshot: {
          accountId: "acct-1",
          equity: 10000,
          balance: 10000,
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0,
          weeklyLossPct: 0,
        },
      }),
    );

    const today = new Date().toISOString().slice(0, 10);
    const stableBase = "https://financialmodelingprep.com/stable/economic-calendar";
    const v3Base = "https://financialmodelingprep.com/api/v3/economic_calendar";
    const key = env.FMP_API_KEY ?? "";

    results.push(await fmpTest("stable current day header", `${stableBase}?from=${today}&to=${today}`, true));
    results.push(await fmpTest("stable historical header", `${stableBase}?from=2024-01-01&to=2024-01-31`, true));
    results.push(
      await fmpTest(
        "stable historical query fallback",
        `${stableBase}?from=2024-01-01&to=2024-01-31&apikey=${key}`,
        false,
      ),
    );
    results.push(await fmpTest("v3 current day query", `${v3Base}?from=${today}&to=${today}&apikey=${key}`, false));
    results.push(
      await fmpTest("v3 historical query", `${v3Base}?from=2024-01-01&to=2024-01-31&apikey=${key}`, false),
    );

    const report = {
      generatedAtUtc: new Date().toISOString(),
      results,
    };

    await writeFile(path.resolve(process.cwd(), "api_test_report.json"), JSON.stringify(report, null, 2), "utf8");

    for (const result of results) {
      console.log(`RESULT:${JSON.stringify(result)}`);
    }
  } finally {
    await app.close();
  }
}

void main();
