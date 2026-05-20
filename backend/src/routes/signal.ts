import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { evaluateSignalLevelRisk } from "../services/risk-engine";
import { evaluateDailyBreakout } from "../services/strategy";
import { inferScore } from "../services/model-inference";
import { decisionKey, newSignalId } from "../utils/ids";
import { RISK_LIMITS } from "../config/riskLimits";
import { Prisma } from "@prisma/client";

const signalSchema = z.object({
  decisionId: z.string().min(1),
  strategyId: z.string().min(1),
  strategyVersion: z.string().min(1),
  modelVersion: z.string().optional(),
  symbol: z.string().min(1),
  timeframe: z.string().min(1),
  barCloseTimeUtc: z.string().min(1),
  aiScore: z.number().optional(),
  marketSnapshot: z.object({
    symbol: z.string(),
    timeframe: z.string(),
    barCloseTimeUtc: z.string(),
    close1: z.number(),
    sma100_1: z.number(),
    sma200_1: z.number(),
    highestHigh55: z.number(),
    lowestLow55: z.number(),
    atr20_1: z.number(),
    volatility: z.number().positive().describe("Rolling volatility (std dev of returns) from completed bars"),
    spreadPrice: z.number().optional(),
    open0: z.number().optional(),
    close1Prev: z.number().optional(),
  }),
  accountSnapshot: z.object({
    accountId: z.string(),
    equity: z.number().optional(),
    balance: z.number().optional(),
    openRisk: z.number().optional(),
    openTrades: z.number().optional(),
    dailyLossPct: z.number().optional(),
    weeklyLossPct: z.number().optional(),
  }),
});

export async function signalRoutes(app: FastifyInstance): Promise<void> {
  app.post("/signal", async (req, reply) => {
    const parsed = signalSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const input = parsed.data;
    const signalId = newSignalId();
    const evaluatedAtUtc = new Date().toISOString();
    const key = decisionKey(input.strategyId, input.symbol, input.timeframe, input.barCloseTimeUtc);

    const risk = evaluateSignalLevelRisk(input);
    const strategyAction = evaluateDailyBreakout(input);

    // Compute inference features matching training data schema
    // Features: [trend_strength, volatility, spread_atr, breakout_distance, momentum]
    const inferenceFeatures = [
      input.marketSnapshot.close1 - input.marketSnapshot.sma200_1,  // trend_strength
      input.marketSnapshot.volatility,                               // volatility
      (input.marketSnapshot.spreadPrice ?? 0) / Math.max(input.marketSnapshot.atr20_1, 0.000001),  // spread_atr
      input.marketSnapshot.close1 - input.marketSnapshot.highestHigh55,  // breakout_distance
      input.marketSnapshot.close1 - input.marketSnapshot.sma100_1,  // momentum
    ];

    const inference = typeof input.aiScore === "number" ? { score: input.aiScore, status: "APPLIED" as const } : await inferScore(inferenceFeatures);
    const inferredScore = inference.score ?? undefined;
    const aiReasons: string[] = [];
    let sizeBucket: "FULL" | "HALF" | "SKIP" = "FULL";

    if (inference.status === "MODEL_UNAVAILABLE") {
      aiReasons.push("AI_MODEL_UNAVAILABLE");
    }

    if (inference.status === "INFERENCE_ERROR" || inference.status === "INVALID_OUTPUT") {
      aiReasons.push("AI_INFERENCE_ERROR");
    }

    if (inference.status === "INVALID_FEATURES") {
      aiReasons.push("AI_INVALID_FEATURES");
    }

    if (typeof inferredScore === "number") {
      if (inferredScore >= RISK_LIMITS.aiScoreThresholds.full) {
        sizeBucket = "FULL";
        aiReasons.push("AI_SCORE_APPLIED");
      } else if (inferredScore >= RISK_LIMITS.aiScoreThresholds.half) {
        sizeBucket = "HALF";
        aiReasons.push("AI_HALF_SIZE");
        aiReasons.push("AI_SCORE_APPLIED");
      } else {
        sizeBucket = "SKIP";
        aiReasons.push("AI_SKIP");
        aiReasons.push("AI_SCORE_APPLIED");
      }
    }

    const response = {
      decisionId: input.decisionId,
      signalId,
      action: risk.approved && sizeBucket !== "SKIP" ? strategyAction : "HOLD",
      riskDecision: risk.approved ? "APPROVED" : "VETOED",
      reasonCodes: [...risk.reasonCodes, ...aiReasons],
      barCloseTimeUtc: input.barCloseTimeUtc,
      evaluatedAtUtc,
      aiScore: inferredScore,
      sizeBucket,
    };

    try {
      await prismaClient().signal.create({
        data: {
          decisionId: input.decisionId,
          signalId,
          decisionKey: key,
          strategyId: input.strategyId,
          strategyVersion: input.strategyVersion,
          modelVersion: input.modelVersion,
          symbol: input.symbol,
          timeframe: input.timeframe,
          action: response.action,
          barCloseTimeUtc: new Date(input.barCloseTimeUtc),
          evaluatedAtUtc: new Date(evaluatedAtUtc),
          requestJson: input,
          responseJson: response,
        },
      });
    } catch (error) {
      const isDuplicate =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === "P2002";

      if (isDuplicate) {
        const existing = await prismaClient().signal.findFirst({
          where: {
            OR: [{ decisionId: input.decisionId }, { decisionKey: key }],
          },
        });

        if (existing?.responseJson && typeof existing.responseJson === "object") {
          req.log.info({ decisionId: input.decisionId, decisionKey: key }, "signal idempotent replay");
          return existing.responseJson;
        }
      }

      req.log.warn({ error }, "signal persistence failed");
    }

    return response;
  });
}
