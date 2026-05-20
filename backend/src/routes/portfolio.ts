import type { FastifyInstance } from "fastify";
import { Prisma } from "@prisma/client";
import { createHash } from "node:crypto";
import { z } from "zod";
import { evaluateAccountLevelRisk } from "../services/risk-engine";
import { prismaClient } from "../services/prisma";

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

      if (result.approved) {
        approvedPlans.push(plan.decisionId);
        runningOpenRisk += plan.proposedRiskPct;
        runningOpenTrades += 1;
        await tx.portfolioDecisionItem.create({
          data: {
            portfolioDecisionId,
            decisionId: plan.decisionId,
            approved: true,
            reasonCodes: [],
          },
        });
      } else {
        rejectedPlans.push({ decisionId: plan.decisionId, reasonCodes: result.vetoReasonCodes });
        await tx.portfolioDecisionItem.create({
          data: {
            portfolioDecisionId,
            decisionId: plan.decisionId,
            approved: false,
            reasonCodes: result.vetoReasonCodes,
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
