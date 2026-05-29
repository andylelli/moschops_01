import { buildApp } from "./app";
import { env } from "./utils/env";
import { prismaClient } from "./services/prisma";
import { preflightModelInference, getModelLoaderStatus } from "./services/model-inference";
import { recordFileLog } from "./services/file-log";

async function start(): Promise<void> {
  const app = buildApp();
  recordFileLog({
    category: "startup",
    level: "info",
    event: "backend_process_start",
    message: "Backend process startup sequence entered",
    context: { port: env.PORT, nodeEnv: env.NODE_ENV },
  });

  try {
    await prismaClient().$connect();
    await preflightModelInference();

    const modelStatus = getModelLoaderStatus();
    if (modelStatus.state !== "available") {
      app.log.warn({ modelStatus }, "model loader is degraded; AI scoring will be skipped");
      recordFileLog({
        category: "model",
        level: "warn",
        event: "model_loader_degraded",
        message: "model loader is degraded; AI scoring will be skipped",
        context: { modelStatus },
      });
    }

    await app.listen({ port: env.PORT, host: "0.0.0.0" });
    app.log.info({ port: env.PORT }, "backend started");
    recordFileLog({
      category: "startup",
      level: "info",
      event: "backend_started",
      message: "backend started",
      context: { port: env.PORT },
    });
  } catch (error) {
    app.log.error({ error }, "startup failed");
    recordFileLog({
      category: "error",
      level: "error",
      event: "backend_startup_failed",
      message: "startup failed",
      context: { error },
    });
    process.exit(1);
  }
}

void start();
