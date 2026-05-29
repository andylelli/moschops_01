import { env } from "../utils/env";

export type HistoricalTimeframe = "M15" | "H1" | "H4" | "D1";

export interface HistoricalDownloadRequest {
  symbol: string;
  timeframe: HistoricalTimeframe;
  fromDate: string;
  toDate: string;
}

export interface NormalizedHistoricalBar {
  barCloseTimeUtc: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  rawJson: Record<string, unknown>;
}

interface FmpRow {
  date?: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
}

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
}

function buildDateFromValue(value: string): Date | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  let normalized = trimmed;

  // FMP intraday rows use "YYYY-MM-DD HH:mm:ss"; normalize to ISO UTC.
  if (/^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?$/.test(normalized)) {
    normalized = normalized.replace(" ", "T");
  }

  // Date-only values are interpreted as UTC midnight.
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    normalized = `${normalized}T00:00:00Z`;
  }

  // If timestamp lacks timezone marker, default to UTC for deterministic storage.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(normalized)) {
    normalized = `${normalized}Z`;
  }

  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isValidNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeFmpRows(rows: FmpRow[], fromDate: Date, toDate: Date): NormalizedHistoricalBar[] {
  const normalized: NormalizedHistoricalBar[] = [];

  for (const row of rows) {
    const dateValue = typeof row.date === "string" ? buildDateFromValue(row.date) : null;
    if (!dateValue) {
      continue;
    }

    if (!isValidNumber(row.open) || !isValidNumber(row.high) || !isValidNumber(row.low) || !isValidNumber(row.close)) {
      continue;
    }

    if (dateValue < fromDate || dateValue > toDate) {
      continue;
    }

    normalized.push({
      barCloseTimeUtc: dateValue,
      open: row.open,
      high: row.high,
      low: row.low,
      close: row.close,
      volume: isValidNumber(row.volume) ? row.volume : null,
      rawJson: row as unknown as Record<string, unknown>,
    });
  }

  normalized.sort((a, b) => a.barCloseTimeUtc.getTime() - b.barCloseTimeUtc.getTime());
  return normalized;
}

function aggregateToH4(rows: NormalizedHistoricalBar[]): NormalizedHistoricalBar[] {
  const buckets = new Map<string, NormalizedHistoricalBar[]>();

  for (const row of rows) {
    const d = row.barCloseTimeUtc;
    const bucketHour = Math.floor(d.getUTCHours() / 4) * 4;
    const bucketKey = `${d.getUTCFullYear()}-${d.getUTCMonth()}-${d.getUTCDate()}-${bucketHour}`;
    const current = buckets.get(bucketKey) ?? [];
    current.push(row);
    buckets.set(bucketKey, current);
  }

  const result: NormalizedHistoricalBar[] = [];

  for (const bucketRows of buckets.values()) {
    bucketRows.sort((a, b) => a.barCloseTimeUtc.getTime() - b.barCloseTimeUtc.getTime());
    const first = bucketRows[0];
    const last = bucketRows[bucketRows.length - 1];

    const high = Math.max(...bucketRows.map((row) => row.high));
    const low = Math.min(...bucketRows.map((row) => row.low));
    const volumeSum = bucketRows.reduce((sum, row) => sum + (row.volume ?? 0), 0);

    result.push({
      barCloseTimeUtc: last.barCloseTimeUtc,
      open: first.open,
      high,
      low,
      close: last.close,
      volume: volumeSum,
      rawJson: {
        aggregatedFrom: "H1",
        parts: bucketRows.length,
      },
    });
  }

  result.sort((a, b) => a.barCloseTimeUtc.getTime() - b.barCloseTimeUtc.getTime());
  return result;
}

async function fetchJsonWithFallback(paths: string[]): Promise<unknown> {
  if (!env.FMP_API_KEY) {
    throw new Error("FMP_API_KEY is required for historical data download");
  }

  const origin = new URL(env.FMP_BASE_URL).origin;
  let lastError: Error | null = null;

  for (const path of paths) {
    const url = new URL(path, origin);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12_000);

    try {
      let response = await fetch(url, {
        method: "GET",
        headers: {
          apikey: env.FMP_API_KEY,
        },
        signal: controller.signal,
      });

      if (response.status === 401 || response.status === 403) {
        const fallback = new URL(url);
        fallback.searchParams.set("apikey", env.FMP_API_KEY);
        response = await fetch(fallback, { signal: controller.signal });
      }

      if (!response.ok) {
        const message = await response.text();
        throw new Error(`FMP historical request failed (${response.status}): ${message.slice(0, 250)}`);
      }

      return (await response.json()) as unknown;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("Unknown fetch error");
    } finally {
      clearTimeout(timeout);
    }
  }

  throw lastError ?? new Error("Historical data fetch failed");
}

async function fetchD1(symbol: string, fromDate: string, toDate: string): Promise<FmpRow[]> {
  const payload = await fetchJsonWithFallback([
    `/stable/historical-price-eod/full?symbol=${encodeURIComponent(symbol)}&from=${fromDate}&to=${toDate}`,
    `/api/v3/historical-price-full/${encodeURIComponent(symbol)}?from=${fromDate}&to=${toDate}`,
  ]);

  if (Array.isArray(payload)) {
    return payload as FmpRow[];
  }

  if (payload && typeof payload === "object" && Array.isArray((payload as { historical?: unknown[] }).historical)) {
    return (payload as { historical: FmpRow[] }).historical;
  }

  throw new Error("Unexpected D1 payload shape from provider");
}

async function fetchIntraday(symbol: string, interval: "1hour" | "15min", fromDate: string, toDate: string): Promise<FmpRow[]> {
  const payload = await fetchJsonWithFallback([
    `/stable/historical-chart/${interval}?symbol=${encodeURIComponent(symbol)}&from=${fromDate}&to=${toDate}`,
    `/api/v3/historical-chart/${interval}/${encodeURIComponent(symbol)}?from=${fromDate}&to=${toDate}`,
  ]);

  if (!Array.isArray(payload)) {
    throw new Error("Unexpected intraday payload shape from provider");
  }

  return payload as FmpRow[];
}

export async function downloadHistoricalBars(request: HistoricalDownloadRequest): Promise<NormalizedHistoricalBar[]> {
  const symbol = normalizeSymbol(request.symbol);
  const fromDate = buildDateFromValue(request.fromDate);
  const toDate = buildDateFromValue(request.toDate);

  if (!fromDate || !toDate) {
    throw new Error("Invalid fromDate or toDate. Use YYYY-MM-DD format.");
  }

  if (fromDate > toDate) {
    throw new Error("fromDate must be before or equal to toDate");
  }

  if (request.timeframe === "D1") {
    const rows = await fetchD1(symbol, request.fromDate, request.toDate);
    return normalizeFmpRows(rows, fromDate, toDate);
  }

  if (request.timeframe === "H1") {
    const rows = await fetchIntraday(symbol, "1hour", request.fromDate, request.toDate);
    return normalizeFmpRows(rows, fromDate, toDate);
  }

  if (request.timeframe === "M15") {
    const rows = await fetchIntraday(symbol, "15min", request.fromDate, request.toDate);
    return normalizeFmpRows(rows, fromDate, toDate);
  }

  if (request.timeframe === "H4") {
    const rows = await fetchIntraday(symbol, "1hour", request.fromDate, request.toDate);
    return aggregateToH4(normalizeFmpRows(rows, fromDate, toDate));
  }

  throw new Error(`Unsupported timeframe ${request.timeframe}`);
}
