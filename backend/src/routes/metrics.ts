import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";

const scoreDistributionQuerySchema = z.object({
  strategyId: z.string().min(1).optional(),
  bins: z.coerce.number().int().min(5).max(20).default(10),
  lookback: z.coerce.number().int().min(50).max(5000).default(1000),
});

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

  app.get("/score-distribution", async (req, reply) => {
    const parsed = scoreDistributionQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const where = parsed.data.strategyId
      ? {
          strategyId: parsed.data.strategyId,
        }
      : {};

    const predictions = await prismaClient().modelPrediction.findMany({
      where,
      orderBy: { createdAt: "desc" },
      take: parsed.data.lookback,
      select: {
        predictionScore: true,
      },
    });

    const bins = Array.from({ length: parsed.data.bins }, (_value, index) => {
      const lower = index / parsed.data.bins;
      const upper = (index + 1) / parsed.data.bins;
      return {
        label: `${lower.toFixed(1)}-${upper.toFixed(1)}`,
        lower,
        upper,
        count: 0,
      };
    });

    for (const prediction of predictions) {
      const bounded = Math.min(Math.max(prediction.predictionScore, 0), 1);
      const targetIndex = Math.min(Math.floor(bounded * parsed.data.bins), parsed.data.bins - 1);
      bins[targetIndex].count += 1;
    }

    return {
      count: predictions.length,
      bins,
    };
  });
}
