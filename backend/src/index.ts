import { buildApp } from "./app";
import { env } from "./utils/env";
import { prismaClient } from "./services/prisma";
import { preflightModelInference, getModelLoaderStatus } from "./services/model-inference";

async function start(): Promise<void> {
  const app = buildApp();

  try {
    await prismaClient().$connect();
    await preflightModelInference();

    const modelStatus = getModelLoaderStatus();
    if (modelStatus.state !== "available") {
      app.log.warn({ modelStatus }, "model loader is degraded; AI scoring will be skipped");
    }

    await app.listen({ port: env.PORT, host: "0.0.0.0" });
    app.log.info({ port: env.PORT }, "backend started");
  } catch (error) {
    app.log.error({ error }, "startup failed");
    process.exit(1);
  }
}

void start();
