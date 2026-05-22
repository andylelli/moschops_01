import { env } from "../utils/env";

interface ProbeResult {
  source: "fmp";
  name: string;
  status: number;
  ok: boolean;
  itemCount: number | null;
  summary: string;
}

async function runProbe(name: string, url: string, headers?: Record<string, string>): Promise<ProbeResult> {
  const response = await fetch(url, { headers });
  const text = await response.text();

  let itemCount: number | null = null;
  let summary = "body:empty";

  if (text) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (Array.isArray(parsed)) {
        itemCount = parsed.length;
        summary = `count:${parsed.length}`;
      } else if (parsed && typeof parsed === "object") {
        const maybe = parsed as Record<string, unknown>;
        if (typeof maybe.error === "string") {
          summary = `error:${maybe.error}`;
        } else if (typeof maybe.Error === "string") {
          summary = `error:${maybe.Error}`;
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
    itemCount,
    summary,
  };
}

async function main(): Promise<void> {
  const key = env.FMP_API_KEY;
  if (!key) {
    throw new Error("FMP_API_KEY missing");
  }

  const today = new Date().toISOString().slice(0, 10);
  const stableBase = "https://financialmodelingprep.com/stable/economic-calendar";
  const v3Base = "https://financialmodelingprep.com/api/v3/economic_calendar";

  const tests: Array<Promise<ProbeResult>> = [
    runProbe("stable current day header", `${stableBase}?from=${today}&to=${today}`, { apikey: key }),
    runProbe("stable historical header", `${stableBase}?from=2024-01-01&to=2024-01-31`, { apikey: key }),
    runProbe("stable historical query fallback", `${stableBase}?from=2024-01-01&to=2024-01-31&apikey=${key}`),
    runProbe("v3 current day query", `${v3Base}?from=${today}&to=${today}&apikey=${key}`),
    runProbe("v3 historical query", `${v3Base}?from=2024-01-01&to=2024-01-31&apikey=${key}`),
  ];

  const results = await Promise.all(tests);
  for (const result of results) {
    console.log(`RESULT:${JSON.stringify(result)}`);
  }
}

void main();
