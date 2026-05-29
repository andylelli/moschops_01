import type { FastifyInstance } from "fastify";
import { Prisma } from "@prisma/client";
import { createHash } from "node:crypto";
import { z } from "zod";
import { evaluateAccountLevelRisk } from "../services/risk-engine";
import { prismaClient } from "../services/prisma";
import { evaluateNewsPolicy } from "../services/news-policy";

const portfolioSchema = z.object({
  accountSnapshot: z.object({
    accountId: z.string(),
    openRisk: z.number().optional(),
    openTrades: z.number().optional(),
    dailyLossPct: z.number().optional(),
    weeklyLossPct: z.number().optional(),
  }),
  plans: z.array(
    z.object({
      decisionId: z.string(),
      strategyId: z.string(),
      symbol: z.string(),
      proposedRiskPct: z.number().nonnegative(),
    })
  ),
  portfolioDecisionId: z.string().min(1).optional(),
  maxOpenRisk: z.number().default(0.04),
  maxOpenTrades: z.number().default(6),
});

const portfolioSummaryQuerySchema = z.object({
  maxOpenRisk: z.coerce.number().positive().default(0.04),
  maxOpenTrades: z.coerce.number().int().positive().default(6),
  lookback: z.coerce.number().int().min(20).max(1000).default(200),
});

function classifyAssetClass(symbol: string): string {
  const normalized = symbol.toUpperCase();

  if (normalized.includes("XAU") || normalized.includes("XAG")) {
    return "Metals";
  }

  if (normalized.length === 6 && /^[A-Z]+$/.test(normalized)) {
    return "FX";
  }

  if (normalized.includes("US") || normalized.includes("JP") || normalized.includes("DE")) {
    return "Index";
  }

  return "Other";
}

function asPortfolioResponse(decision: {
  portfolioDecisionId: string;
  approvedPlans: string[];
  rejectedPlans: Prisma.JsonValue;
  remainingRiskBudget: number;
  remainingTradeSlots: number;
  evaluatedAtUtc: Date;
}) {
  return {
    portfolioDecisionId: decision.portfolioDecisionId,
    approvedPlans: decision.approvedPlans,
    rejectedPlans: Array.isArray(decision.rejectedPlans) ? decision.rejectedPlans : [],
    remainingRiskBudget: decision.remainingRiskBudget,
    remainingTradeSlots: decision.remainingTradeSlots,
    evaluatedAtUtc: decision.evaluatedAtUtc.toISOString(),
  };
}

export async function portfolioRoutes(app: FastifyInstance): Promise<void> {
  app.get("/portfolio/summary", async (req, reply) => {
    const parsed = portfolioSummaryQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const [latestDecision, openSnapshots, recentDecisionItems] = await Promise.all([
      prismaClient().portfolioDecision.findFirst({
        orderBy: { evaluatedAtUtc: "desc" },
      }),
      prismaClient().openTradeSnapshot.findMany({
        orderBy: { capturedAtUtc: "desc" },
        take: parsed.data.lookback,
      }),
      prismaClient().portfolioDecisionItem.findMany({
        where: { approved: false },
        orderBy: { createdAt: "desc" },
        take: parsed.data.lookback,
      }),
    ]);

    const symbolCounts = new Map<string, number>();
    for (const snapshot of openSnapshots) {
      const symbol = (snapshot.symbol ?? "UNKNOWN").toUpperCase();
      symbolCounts.set(symbol, (symbolCounts.get(symbol) ?? 0) + 1);
    }

    const totalExposureRows = Array.from(symbolCounts.values()).reduce((sum, count) => sum + count, 0);
    const exposureBySymbol = Array.from(symbolCounts.entries())
      .map(([symbol, count]) => ({
        symbol,
        count,
        sharePct: totalExposureRows > 0 ? (count / totalExposureRows) * 100 : 0,
        assetClass: classifyAssetClass(symbol),
      }))
      .sort((a, b) => b.count - a.count);

    const vetoCounts = new Map<string, number>();
    for (const item of recentDecisionItems) {
      for (const reasonCode of item.reasonCodes) {
        vetoCounts.set(reasonCode, (vetoCounts.get(reasonCode) ?? 0) + 1);
      }
    }

    const vetoBreakdownTop = Array.from(vetoCounts.entries())
      .map(([reasonCode, count]) => ({ reasonCode, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    const correlationFlags = vetoBreakdownTop
      .filter((item) => item.reasonCode.toUpperCase().includes("CORRELATION"))
      .reduce((sum, item) => sum + item.count, 0);

    const totalRejected = Array.from(vetoCounts.values()).reduce((sum, count) => sum + count, 0);
    const maxOpenRisk = parsed.data.maxOpenRisk;
    const maxOpenTrades = parsed.data.maxOpenTrades;

    const remainingRiskBudget = latestDecision?.remainingRiskBudget ?? maxOpenRisk;
    const remainingTradeSlots = latestDecision?.remainingTradeSlots ?? maxOpenTrades;

    return {
      generatedAtUtc: new Date().toISOString(),
      sourceDecisionId: latestDecision?.portfolioDecisionId ?? null,
      exposureBySymbol,
      openRiskBudget: {
        maxOpenRisk,
        remainingRiskBudget,
        consumedRiskBudget: Math.max(0, maxOpenRisk - remainingRiskBudget),
        consumedPct: maxOpenRisk > 0 ? Math.min(100, Math.max(0, ((maxOpenRisk - remainingRiskBudget) / maxOpenRisk) * 100)) : 0,
      },
      tradeSlots: {
        maxOpenTrades,
        remainingTradeSlots,
        consumedTradeSlots: Math.max(0, maxOpenTrades - remainingTradeSlots),
        consumedPct: maxOpenTrades > 0 ? Math.min(100, Math.max(0, ((maxOpenTrades - remainingTradeSlots) / maxOpenTrades) * 100)) : 0,
      },
      vetoBreakdownTop,
      correlationConcentration: {
        flaggedCount: correlationFlags,
        totalRejected,
        ratioPct: totalRejected > 0 ? (correlationFlags / totalRejected) * 100 : 0,
      },
    };
  });

  app.post("/portfolio/evaluate", async (req, reply) => {
    const parsed = portfolioSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const body = parsed.data;
    const requestHash = createHash("sha256")
      .update(
        JSON.stringify({
          accountSnapshot: body.accountSnapshot,
          plans: body.plans,
          maxOpenRisk: body.maxOpenRisk,
          maxOpenTrades: body.maxOpenTrades,
        })
      )
      .digest("hex");

    const existingById = body.portfolioDecisionId
      ? await prismaClient().portfolioDecision.findUnique({
          where: { portfolioDecisionId: body.portfolioDecisionId },
        })
      : null;
    if (existingById) {
      return asPortfolioResponse(existingById);
    }

    const existingByHash = await prismaClient().portfolioDecision.findUnique({
      where: { requestHash },
    });
    if (existingByHash) {
      return asPortfolioResponse(existingByHash);
    }

    const portfolioDecisionId =
      body.portfolioDecisionId ??
      `portfolio-${body.accountSnapshot.accountId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    try {
      const response = await prismaClient().$transaction(async (tx) => {
        await tx.portfolioDecision.create({
          data: {
            portfolioDecisionId,
            requestHash,
            accountId: body.accountSnapshot.accountId,
            requestJson: body,
            approvedPlans: [],
            rejectedPlans: [],
            remainingRiskBudget: body.maxOpenRisk,
            remainingTradeSlots: body.maxOpenTrades,
            evaluatedAtUtc: new Date(),
          },
        });

        let runningOpenRisk = body.accountSnapshot.openRisk ?? 0;
        let runningOpenTrades = body.accountSnapshot.openTrades ?? 0;

        const approvedPlans: string[] = [];
        const rejectedPlans: Array<{ decisionId: string; reasonCodes: string[] }> = [];

    for (const plan of body.plans) {
      const result = evaluateAccountLevelRisk({
        decisionId: plan.decisionId,
        strategyId: plan.strategyId,
        symbol: plan.symbol,
        proposedRiskPct: plan.proposedRiskPct,
        proposedOpenTrades: 1,
        maxOpenRisk: body.maxOpenRisk,
        maxOpenTrades: body.maxOpenTrades,
        accountSnapshot: {
          accountId: body.accountSnapshot.accountId,
          openRisk: runningOpenRisk,
          openTrades: runningOpenTrades,
          dailyLossPct: body.accountSnapshot.dailyLossPct,
          weeklyLossPct: body.accountSnapshot.weeklyLossPct,
        },
      });

      const newsPolicy = await evaluateNewsPolicy({
        symbol: plan.symbol,
        isEntryAction: true,
        db: tx,
      });

      const reasonCodes = [...result.vetoReasonCodes, ...newsPolicy.reasonCodes];
      const blockedByNews = newsPolicy.policyAction === "BLOCK_NEW";

      if (result.approved && !blockedByNews) {
        const riskMultiplier = newsPolicy.policyAction === "REDUCE" ? 0.5 : 1;
        approvedPlans.push(plan.decisionId);
        runningOpenRisk += plan.proposedRiskPct * riskMultiplier;
        runningOpenTrades += 1;
        await tx.portfolioDecisionItem.create({
          data: {
            portfolioDecisionId,
            decisionId: plan.decisionId,
            approved: true,
            reasonCodes,
          },
        });
      } else {
        rejectedPlans.push({ decisionId: plan.decisionId, reasonCodes });
        await tx.portfolioDecisionItem.create({
          data: {
            portfolioDecisionId,
            decisionId: plan.decisionId,
            approved: false,
            reasonCodes,
          },
        });
      }
    }

        const result = {
          portfolioDecisionId,
          approvedPlans,
          rejectedPlans,
          remainingRiskBudget: Math.max(0, body.maxOpenRisk - runningOpenRisk),
          remainingTradeSlots: Math.max(0, body.maxOpenTrades - runningOpenTrades),
          evaluatedAtUtc: new Date().toISOString(),
        };

        await tx.portfolioDecision.update({
          where: { portfolioDecisionId },
          data: {
            approvedPlans,
            rejectedPlans,
            remainingRiskBudget: result.remainingRiskBudget,
            remainingTradeSlots: result.remainingTradeSlots,
            evaluatedAtUtc: new Date(result.evaluatedAtUtc),
          },
        });

        return result;
      });

      return response;
    } catch (error) {
      const isDuplicate =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === "P2002";

      if (isDuplicate) {
        const replay = await prismaClient().portfolioDecision.findFirst({
          where: {
            OR: [{ portfolioDecisionId }, { requestHash }],
          },
        });
        if (replay) {
          return asPortfolioResponse(replay);
        }
      }

      req.log.error({ error, portfolioDecisionId }, "portfolio evaluation failed");
      return reply.status(500).send({
        error: {
          code: "PORTFOLIO_EVAL_FAILED",
          portfolioDecisionId,
        },
      });
    };
  });
}
