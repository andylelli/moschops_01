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
import { startNewsSync } from "./services/news-sync";
import { ensureActiveModelVersionRecord } from "./services/model-metadata";

export function buildApp(): FastifyInstance {
  // Validate configuration at app startup
  validateRiskLimits();

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

  app.addHook("onReady", async () => {
    await ensureActiveModelVersionRecord(app.log);
  });

  const stopNewsSync = startNewsSync(app.log);
  app.addHook("onClose", async () => {
    stopNewsSync();
  });

  return app;
}
