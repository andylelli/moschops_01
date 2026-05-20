import type { FastifyInstance } from "fastify";
import { prismaClient } from "../services/prisma";
import { getModelLoaderStatus } from "../services/model-inference";

export async function healthRoutes(app: FastifyInstance): Promise<void> {
  app.get("/health", async () => {
    let db = "up";
    try {
      await prismaClient().$queryRaw`SELECT 1`;
    } catch {
      db = "down";
    }

    const modelStatus = getModelLoaderStatus();

    return {
      status: "ok",
      service: "moschops-backend",
      timestamp: new Date().toISOString(),
      telemetry: {
        backend: "up",
        database: db,
        modelLoader: modelStatus.state,
        modelReason: modelStatus.reason,
      },
    };
  });
}
