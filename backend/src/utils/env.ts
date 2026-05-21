import "dotenv/config";
import { z } from "zod";

/**
 * Environment variable schema validation.
 * Ensures all required config is present and valid at startup.
 */
const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  PORT: z.coerce.number().int().positive().default(3000),
  DATABASE_URL: z.string().url("DATABASE_URL must be a valid PostgreSQL connection URL"),
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
    process.exit(1);
  }

  return result.data;
}

export const env = parseEnv();
