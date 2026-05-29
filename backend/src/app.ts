import Fastify, { type FastifyInstance } from "fastify";
import cors from "@fastify/cors";
import sensible from "@fastify/sensible";
import { env } from "./utils/env";
import { validateRiskLimits } from "./config/riskLimits";
import { healthRoutes } from "./routes/health";
import { signalRoutes } from "./routes/signal";
import { riskRoutes } from "./routes/risk";
import { loggingRoutes } from "./routes/logging";
import { metricsRoutes } from "./routes/metrics";
import { openTradesRoutes } from "./routes/trades-open";
import { portfolioRoutes } from "./routes/portfolio";
import { newsRoutes } from "./routes/news";
import { historicalDataRoutes } from "./routes/historical-data";
import { strategyConfigRoutes } from "./routes/strategy-config";
import { trainingRoutes } from "./routes/training";
import { adminRoutes } from "./routes/admin";
import { incidentsRoutes } from "./routes/incidents";
import { startNewsSync } from "./services/news-sync";
import { ensureActiveModelVersionRecord } from "./services/model-metadata";
import { configureFileLogRoot, recordFileLog, recordHttpError, recordHttpRequest, recordHttpResponse } from "./services/file-log";

export function buildApp(): FastifyInstance {
  const shouldUseDatabase = env.NODE_ENV !== "test" || process.env.RUN_DB_TESTS === "true";
  const shouldWriteFileLogs = env.LOG_TO_FILES && env.NODE_ENV !== "test";

  // Validate configuration at app startup
  validateRiskLimits();

  if (shouldWriteFileLogs) {
    configureFileLogRoot(env.LOG_DIR);
    recordFileLog({
      category: "startup",
      level: "info",
      event: "backend_build_started",
      message: "Backend application boot sequence started",
      context: { nodeEnv: env.NODE_ENV, logDir: env.LOG_DIR },
    });
  }

  const app = Fastify({
    logger: {
      level: env.LOG_LEVEL,
      transport: env.NODE_ENV === "development" ? { target: "pino-pretty" } : undefined,
    },
  });

  void app.register(cors, {
    origin: true,
    methods: ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  });
  void app.register(sensible);

  void app.register(healthRoutes);
  void app.register(signalRoutes);
  void app.register(riskRoutes);
  void app.register(loggingRoutes);
  void app.register(metricsRoutes);
  void app.register(openTradesRoutes);
  void app.register(portfolioRoutes);
  void app.register(newsRoutes);
  void app.register(historicalDataRoutes);
  void app.register(strategyConfigRoutes);
  void app.register(trainingRoutes);
  void app.register(adminRoutes);
  void app.register(incidentsRoutes);

  app.addHook("onRequest", async (request) => {
    if (!shouldWriteFileLogs) {
      return;
    }

    (request as typeof request & { fileLogStartAt?: number }).fileLogStartAt = Date.now();
    recordHttpRequest({
      method: request.method,
      url: request.url,
      requestId: request.id,
      remoteAddress: request.ip,
      userAgent: request.headers["user-agent"]?.toString(),
      route: request.routeOptions?.url,
    });
  });

  app.addHook("onResponse", async (request, reply) => {
    if (!shouldWriteFileLogs) {
      return;
    }

    const startedAt = (request as typeof request & { fileLogStartAt?: number }).fileLogStartAt ?? Date.now();
    recordHttpResponse({
      method: request.method,
      url: request.url,
      requestId: request.id,
      remoteAddress: request.ip,
      userAgent: request.headers["user-agent"]?.toString(),
      route: request.routeOptions?.url,
      statusCode: reply.statusCode,
      durationMs: Date.now() - startedAt,
    });
  });

  app.addHook("onError", async (request, reply, error) => {
    if (!shouldWriteFileLogs) {
      return;
    }

    const startedAt = (request as typeof request & { fileLogStartAt?: number }).fileLogStartAt ?? Date.now();
    recordHttpError({
      method: request.method,
      url: request.url,
      requestId: request.id,
      remoteAddress: request.ip,
      userAgent: request.headers["user-agent"]?.toString(),
      route: request.routeOptions?.url,
      statusCode: reply.statusCode,
      durationMs: Date.now() - startedAt,
      error,
    });
  });

  app.addHook("onReady", async () => {
    if (!shouldUseDatabase) {
      app.log.info("model metadata bootstrap skipped in non-DB test mode");
      if (shouldWriteFileLogs) {
        recordFileLog({
          category: "startup",
          level: "info",
          event: "model_metadata_bootstrap_skipped",
          message: "model metadata bootstrap skipped in non-DB test mode",
        });
      }
      return;
    }

    try {
      await ensureActiveModelVersionRecord(app.log);
    } catch (error) {
      app.log.warn({ error }, "model metadata bootstrap skipped due to persistence unavailability");
      if (shouldWriteFileLogs) {
        recordFileLog({
          category: "db",
          level: "warn",
          event: "model_metadata_bootstrap_skipped",
          message: "model metadata bootstrap skipped due to persistence unavailability",
          context: { error },
        });
      }
    }
  });

  const stopNewsSync = startNewsSync(app.log);
  app.addHook("onClose", async () => {
    if (shouldWriteFileLogs) {
      recordFileLog({
        category: "startup",
        level: "info",
        event: "backend_shutdown",
        message: "Backend application is shutting down",
      });
    }
    stopNewsSync();
  });

  return app;
}
