import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { defaultStrategyRuntimeProfile, loadStrategyRuntimeProfile } from "../services/strategy-config";

const strategyQuerySchema = z.object({
  strategyId: z.string().min(1).default("daily-breakout-5-10"),
  strategyVersion: z.string().min(1).default("1.0.0"),
});

const updateConfigSchema = z.object({
  strategyId: z.string().min(1),
  strategyVersion: z.string().min(1),
  riskProfile: z.string().min(1).default("balanced"),
  config: z.object({
    aiThresholds: z
      .object({
        full: z.number().gt(0).lte(1),
        half: z.number().gt(0).lte(1),
      })
      .refine((value) => value.half < value.full, {
        message: "aiThresholds.half must be lower than aiThresholds.full",
      }),
    aiMandatory: z.boolean(),
    trainingDefaults: z.object({
      datasetProfile: z.string().min(1),
      horizonBars: z.number().int().min(1).max(64),
      cvFolds: z.number().int().min(2).max(20),
      calibration: z.enum(["isotonic", "platt", "none"]),
      threshold: z.number().gt(0).lte(1),
      includeMacro: z.boolean(),
      includeNewsWindows: z.boolean(),
      includeSessionFeatures: z.boolean(),
      enableClassWeights: z.boolean(),
    }),
  }),
});

export async function strategyConfigRoutes(app: FastifyInstance): Promise<void> {
  app.get("/strategy-config/current", async (req, reply) => {
    const parsed = strategyQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const profile = await loadStrategyRuntimeProfile(parsed.data.strategyId, parsed.data.strategyVersion);
    return profile;
  });

  app.put("/strategy-config/current", async (req, reply) => {
    const parsed = updateConfigSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const payload = parsed.data;
    await prismaClient().strategyConfig.create({
      data: {
        strategyId: payload.strategyId,
        strategyVersion: payload.strategyVersion,
        riskProfile: payload.riskProfile,
        configJson: payload.config,
      },
    });

    const profile = await loadStrategyRuntimeProfile(payload.strategyId, payload.strategyVersion);
    return profile;
  });

  app.post("/strategy-config/reset", async (req, reply) => {
    const parsed = strategyQuerySchema.safeParse(req.body ?? {});
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const defaults = defaultStrategyRuntimeProfile(parsed.data.strategyId, parsed.data.strategyVersion);
    await prismaClient().strategyConfig.create({
      data: {
        strategyId: defaults.strategyId,
        strategyVersion: defaults.strategyVersion,
        riskProfile: defaults.riskProfile,
        configJson: defaults.config,
      },
    });

    return {
      ok: true,
      profile: await loadStrategyRuntimeProfile(parsed.data.strategyId, parsed.data.strategyVersion),
    };
  });
}
