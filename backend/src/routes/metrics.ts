import type { FastifyInstance } from "fastify";
import { prismaClient } from "../services/prisma";

export async function metricsRoutes(app: FastifyInstance): Promise<void> {
  app.get("/model-version", async (_req, reply) => {
    const model = await prismaClient().modelVersion.findFirst({
      orderBy: { createdAt: "desc" },
    });

    if (!model) {
      return reply.status(404).send({ error: { code: "MODEL_NOT_FOUND", message: "No model version found" } });
    }

    return {
      strategyId: model.strategyId,
      strategyVersion: model.strategyVersion,
      modelVersion: model.modelVersion,
      lifecycleState: model.lifecycleState,
      createdAt: model.createdAt,
    };
  });

  app.get("/performance", async () => {
    const latest = await prismaClient().performanceSnapshot.findMany({
      orderBy: { capturedAtUtc: "desc" },
      take: 50,
    });

    return {
      count: latest.length,
      items: latest,
    };
  });
}
