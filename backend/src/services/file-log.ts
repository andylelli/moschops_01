import fs from "node:fs";
import path from "node:path";

export type LogLevel = "debug" | "info" | "warn" | "error";

export type LogCategory =
  | "app"
  | "audit"
  | "db"
  | "error"
  | "http"
  | "model"
  | "news"
  | "security"
  | "startup"
  | "system"
  | "training";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

interface RecordLogInput {
  category: LogCategory;
  level: LogLevel;
  event: string;
  message: string;
  context?: unknown;
}

interface HttpRequestLogInput {
  method: string;
  url: string;
  requestId: string;
  remoteAddress: string | undefined;
  userAgent: string | undefined;
  route?: string | undefined;
}

interface HttpResponseLogInput extends HttpRequestLogInput {
  statusCode: number;
  durationMs: number;
}

const logCategories: LogCategory[] = ["app", "audit", "db", "error", "http", "model", "news", "security", "startup", "system", "training"];
const redactedKeys = new Set(["authorization", "cookie", "set-cookie", "password", "secret", "token", "apikey", "apiKey", "x-api-key"]);

let configuredRootDir = path.resolve(process.cwd(), "logs");
let directoriesReady = false;

function ensureDirectories(): void {
  if (directoriesReady) {
    return;
  }

  fs.mkdirSync(configuredRootDir, { recursive: true });
  for (const category of logCategories) {
    fs.mkdirSync(path.join(configuredRootDir, category), { recursive: true });
  }

  directoriesReady = true;
}

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function sanitizeValue(value: unknown, depth = 0): JsonValue {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  if (typeof value === "bigint") {
    return value.toString();
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (value instanceof Error) {
    return { name: value.name, message: value.message, stack: value.stack ?? null };
  }

  if (Array.isArray(value)) {
    return value.slice(0, 50).map((item) => sanitizeValue(item, depth + 1));
  }

  if (!isPlainObject(value)) {
    return String(value);
  }

  if (depth >= 4) {
    return "[MaxDepth]";
  }

  const sanitized: Record<string, JsonValue> = {};
  for (const [key, rawValue] of Object.entries(value)) {
    if (redactedKeys.has(key) || redactedKeys.has(key.toLowerCase())) {
      sanitized[key] = "[REDACTED]";
      continue;
    }

    sanitized[key] = sanitizeValue(rawValue, depth + 1);
  }

  return sanitized;
}

function appendRecord(category: LogCategory, payload: Record<string, unknown>): void {
  ensureDirectories();
  const filePath = path.join(configuredRootDir, category, `${todayUtc()}.log`);
  fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`, "utf8");
}

export function configureFileLogRoot(rootDir: string): void {
  configuredRootDir = path.resolve(rootDir);
  directoriesReady = false;
}

export function recordFileLog(input: RecordLogInput): void {
  appendRecord(input.category, {
    timestampUtc: new Date().toISOString(),
    level: input.level,
    event: input.event,
    message: input.message,
    context: sanitizeValue(input.context),
  });
}

export function recordHttpRequest(input: HttpRequestLogInput): void {
  recordFileLog({
    category: "http",
    level: "info",
    event: "http_request",
    message: `${input.method} ${input.url}`,
    context: {
      requestId: input.requestId,
      method: input.method,
      url: input.url,
      route: input.route ?? null,
      remoteAddress: input.remoteAddress ?? null,
      userAgent: input.userAgent ?? null,
    },
  });
}

export function recordHttpResponse(input: HttpResponseLogInput): void {
  recordFileLog({
    category: "http",
    level: input.statusCode >= 500 ? "error" : input.statusCode >= 400 ? "warn" : "info",
    event: "http_response",
    message: `${input.method} ${input.url} -> ${input.statusCode}`,
    context: {
      requestId: input.requestId,
      method: input.method,
      url: input.url,
      route: input.route ?? null,
      remoteAddress: input.remoteAddress ?? null,
      userAgent: input.userAgent ?? null,
      statusCode: input.statusCode,
      durationMs: input.durationMs,
    },
  });
}

export function recordHttpError(input: HttpRequestLogInput & { statusCode?: number; error: unknown; durationMs?: number }): void {
  recordFileLog({
    category: "error",
    level: "error",
    event: "http_error",
    message: `${input.method} ${input.url}`,
    context: {
      requestId: input.requestId,
      method: input.method,
      url: input.url,
      route: input.route ?? null,
      remoteAddress: input.remoteAddress ?? null,
      userAgent: input.userAgent ?? null,
      statusCode: input.statusCode ?? null,
      durationMs: input.durationMs ?? null,
      error: sanitizeValue(input.error),
    },
  });
}