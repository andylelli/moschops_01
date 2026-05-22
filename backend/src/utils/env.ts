import "dotenv/config";
import { z } from "zod";

function parseBooleanLike(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "number") {
    return value !== 0;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "y", "on"].includes(normalized)) {
      return true;
    }
    if (["0", "false", "no", "n", "off", ""].includes(normalized)) {
      return false;
    }
  }

  return Boolean(value);
}

/**
 * Environment variable schema validation.
 * Ensures all required config is present and valid at startup.
 */
const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  PORT: z.coerce.number().int().positive().default(3000),
  DATABASE_URL: z.string().url("DATABASE_URL must be a valid PostgreSQL connection URL"),
  NEWS_PROVIDER: z.enum(["FMP"]).default("FMP"),
  NEWS_PROVIDER_TIER: z.enum(["FREE", "BASIC"]).default("FREE"),
  NEWS_SYNC_ENABLED: z.preprocess(parseBooleanLike, z.boolean()).default(true),
  FMP_BASE_URL: z.string().url().default("https://financialmodelingprep.com"),
  FMP_API_KEY: z.string().optional(),
  NEWS_SYNC_INTERVAL_MINUTES: z.coerce.number().int().min(1).max(60).default(10),
  NEWS_LOOKAHEAD_DAYS: z.coerce.number().int().min(1).max(90).default(14),
  NEWS_LOOKBACK_DAYS: z.coerce.number().int().min(0).max(30).default(1),
  NEWS_BUDGET_DAILY: z.coerce.number().int().min(1).default(250),
  NEWS_BUDGET_RESERVE_PCT: z.coerce.number().int().min(5).max(90).default(25),
  NEWS_STALE_MINUTES: z.coerce.number().int().min(5).default(30),
  NEWS_DEGRADED_MINUTES: z.coerce.number().int().min(5).default(15),
  NEWS_ENABLED_SYMBOLS: z.string().default("EURUSD,GBPUSD,USDJPY,XAUUSD"),
});

export type Env = z.infer<typeof EnvSchema>;

/**
 * Parse and validate environment variables at startup.
 * Fails fast with clear error messages if config is invalid.
 *
 * @returns Validated environment configuration
 * @throws Process exits with code 1 if validation fails
 */
function parseEnv(): Env {
  const result = EnvSchema.safeParse(process.env);

  if (!result.success) {
    console.error("❌ Invalid environment configuration:");
    result.error.issues.forEach((err) => {
      const path = err.path.join(".");
      console.error(`  ✗ ${path}: ${err.message}`);
    });
    console.error("\nRequired variables:");
    console.error("  NODE_ENV (development|production|test)");
    console.error("  LOG_LEVEL (debug|info|warn|error)");
    console.error("  PORT (positive integer, default 3000)");
    console.error("  DATABASE_URL (valid PostgreSQL URL)");
    console.error("  NEWS_PROVIDER (FMP, default FMP)");
    console.error("  NEWS_PROVIDER_TIER (FREE|BASIC, default FREE)");
    console.error("  NEWS_SYNC_ENABLED (true|false, default true)");
    console.error("  FMP_BASE_URL (default https://financialmodelingprep.com)");
    console.error("  FMP_API_KEY (optional but required for provider sync)");
    process.exit(1);
  }

  return result.data;
}

export const env = parseEnv();
