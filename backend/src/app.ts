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

export function buildApp(): FastifyInstance {
  // Validate configuration at app startup
  validateRiskLimits();

  const app = Fastify({
    logger: {
      level: env.LOG_LEVEL,
      transport: env.NODE_ENV === "development" ? { target: "pino-pretty" } : undefined,
    },
  });

  void app.register(cors, { origin: true });
  void app.register(sensible);

  void app.register(healthRoutes);
  void app.register(signalRoutes);
  void app.register(riskRoutes);
  void app.register(loggingRoutes);
  void app.register(metricsRoutes);
  void app.register(openTradesRoutes);
  void app.register(portfolioRoutes);
  void app.register(newsRoutes);

  return app;
}
