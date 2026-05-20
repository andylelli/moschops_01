import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { evaluateAccountLevelRisk } from "../services/risk-engine";
import { prismaClient } from "../services/prisma";

const riskCheckSchema = z.object({
  decisionId: z.string().min(1),
  strategyId: z.string().min(1),
  symbol: z.string().min(1),
  proposedRiskPct: z.number().nonnegative(),
  proposedOpenTrades: z.number().int().nonnegative(),
  maxOpenRisk: z.number().optional(),
  maxOpenTrades: z.number().optional(),
  dailyLossLimitPct: z.number().optional(),
  weeklyLossLimitPct: z.number().optional(),
  accountSnapshot: z.object({
    accountId: z.string(),
    openRisk: z.number().optional(),
    openTrades: z.number().optional(),
    dailyLossPct: z.number().optional(),
    weeklyLossPct: z.number().optional(),
  }),
});

export async function riskRoutes(app: FastifyInstance): Promise<void> {
  app.post("/risk-check", async (req, reply) => {
    const parsed = riskCheckSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const result = evaluateAccountLevelRisk(parsed.data);

    try {
      if (!result.approved) {
        await prismaClient().riskEvent.create({
          data: {
            decisionId: parsed.data.decisionId,
            strategyId: parsed.data.strategyId,
            eventType: "RISK_VETO",
            reasonCode: result.vetoReasonCodes.join(",") || "UNKNOWN",
            severity: "warning",
            detailsJson: parsed.data,
          },
        });
      }
    } catch (error) {
      req.log.warn({ error }, "risk event persistence failed");
    }

    return result;
  });
}
