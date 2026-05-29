import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { evaluateSignalLevelRisk } from "../services/risk-engine";
import { evaluateDailyBreakout } from "../services/strategy";
import { inferScore } from "../services/model-inference";
import { decisionKey, newSignalId } from "../utils/ids";
import { RISK_LIMITS } from "../config/riskLimits";
import { Prisma } from "@prisma/client";
import { evaluateNewsPolicy } from "../services/news-policy";
import { isEntryAction } from "../services/news-domain";
import { buildInferenceFeatures } from "../services/feature-schema";
import { loadStrategyRuntimeProfile } from "../services/strategy-config";
import { checkCircuitBreaker } from "../services/circuit-breaker";
import { recordBarVolatility, getRegimeStatus } from "../services/regime-gate";

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
    const strategyProfile = await loadStrategyRuntimeProfile(input.strategyId, input.strategyVersion);
    const aiThresholds = strategyProfile.config.aiThresholds;
    const aiMandatory = strategyProfile.config.aiMandatory;
    const newsPolicy = await evaluateNewsPolicy({
      symbol: input.symbol,
      isEntryAction: isEntryAction(strategyAction),
    });

    const inferenceFeatures = buildInferenceFeatures(input.marketSnapshot);

    const inference = typeof input.aiScore === "number" ? { score: input.aiScore, status: "APPLIED" as const } : await inferScore(inferenceFeatures);
    const inferredScore = inference.score ?? undefined;
    const aiReasons: string[] = [];
    let sizeBucket: "FULL" | "HALF" | "SKIP" = "FULL";

    // --- Regime Gate: record volatility and derive adjusted AI thresholds ---
    recordBarVolatility(input.strategyId, input.symbol, input.timeframe, input.marketSnapshot.volatility);
    const regimeStatus = getRegimeStatus(input.strategyId, input.symbol, input.timeframe);
    const regimeBump = regimeStatus.thresholdBump;
    const effectiveThresholds = {
      full: aiThresholds.full + regimeBump,
      half: aiThresholds.half + regimeBump,
    };
    if (regimeBump > 0) {
      aiReasons.push(`REGIME_GATE:${regimeStatus.regimeLabel}:bump=${regimeBump.toFixed(2)}`);
    }
    // -----------------------------------------------------------------------

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
      if (inferredScore >= effectiveThresholds.full) {
        sizeBucket = "FULL";
        aiReasons.push("AI_SCORE_APPLIED");
      } else if (inferredScore >= effectiveThresholds.half) {
        sizeBucket = "HALF";
        aiReasons.push("AI_HALF_SIZE");
        aiReasons.push("AI_SCORE_APPLIED");
      } else {
        sizeBucket = "SKIP";
        aiReasons.push("AI_SKIP");
        aiReasons.push("AI_SCORE_APPLIED");
      }
    }

    if (aiMandatory && typeof inferredScore !== "number") {
      sizeBucket = "SKIP";
      aiReasons.push("AI_MANDATORY_BLOCK");
    }

    // --- Circuit Breaker: daily/weekly loss limits and consecutive losses ---
    const cbStatus = checkCircuitBreaker(
      input.strategyId,
      input.accountSnapshot.dailyLossPct ?? 0,
      input.accountSnapshot.weeklyLossPct ?? 0,
      RISK_LIMITS.maxConsecutiveLosses,
      RISK_LIMITS.dailyLossLimitPct,
      RISK_LIMITS.weeklyLossLimitPct,
    );
    if (cbStatus.tripped) {
      sizeBucket = "SKIP";
      for (const reason of cbStatus.reasons) {
        aiReasons.push(reason);
      }
    }
    // -----------------------------------------------------------------------

    const riskApproved = risk.approved && newsPolicy.policyAction !== "BLOCK_NEW";

    const response = {
      decisionId: input.decisionId,
      signalId,
      action:
        riskApproved && sizeBucket !== "SKIP"
          ? newsPolicy.policyAction === "REDUCE" && isEntryAction(strategyAction)
            ? "REDUCE"
            : strategyAction
          : "HOLD",
      riskDecision: riskApproved ? "APPROVED" : "VETOED",
      reasonCodes: [...risk.reasonCodes, ...newsPolicy.reasonCodes, ...aiReasons],
      barCloseTimeUtc: input.barCloseTimeUtc,
      evaluatedAtUtc,
      aiScore: inferredScore,
      sizeBucket,
      newsContext: {
        policyAction: newsPolicy.policyAction,
        provider: newsPolicy.provider,
        freshnessState: newsPolicy.freshnessState,
        newsEventId: newsPolicy.newsEventId ?? null,
      },
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

      if (response.riskDecision === "VETOED") {
        await prismaClient().rejectedSignal.create({
          data: {
            decisionId: input.decisionId,
            signalId,
            strategyId: input.strategyId,
            strategyVersion: input.strategyVersion,
            symbol: input.symbol,
            timeframe: input.timeframe,
            reasonCode: response.reasonCodes.join(",") || "RISK_VETO",
            detailsJson: {
              reasonCodes: response.reasonCodes,
              newsContext: response.newsContext,
            },
          },
        });
      }
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
