import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import { recordFileLog } from "../services/file-log";

const logSignalSchema = z.object({
  decisionId: z.string(),
  signalId: z.string(),
  strategyId: z.string(),
  strategyVersion: z.string(),
  modelVersion: z.string().optional(),
  symbol: z.string(),
  timeframe: z.string(),
  action: z.enum(["BUY", "SELL", "HOLD", "CLOSE", "REDUCE"]),
  barCloseTimeUtc: z.string(),
  evaluatedAtUtc: z.string(),
  payload: z.any().optional(),
});

const logRejectedSchema = z.object({
  decisionId: z.string(),
  signalId: z.string().optional(),
  strategyId: z.string(),
  strategyVersion: z.string(),
  symbol: z.string(),
  timeframe: z.string(),
  reasonCode: z.string(),
  payload: z.any().optional(),
});

const logTradeSchema = z.object({
  tradeId: z.string(),
  decisionId: z.string().optional(),
  signalId: z.string().optional(),
  strategyId: z.string(),
  strategyVersion: z.string(),
  symbol: z.string(),
  side: z.string(),
  volume: z.number(),
  entryPrice: z.number(),
  stopPrice: z.number().optional(),
  takeProfitPrice: z.number().optional(),
  spread: z.number().optional(),
  slippage: z.number().optional(),
  commission: z.number().optional(),
  swap: z.number().optional(),
  status: z.string(),
  closeReason: z.string().optional(),
});

export async function loggingRoutes(app: FastifyInstance): Promise<void> {
  app.post("/log-signal", async (req, reply) => {
    const parsed = logSignalSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const payload = parsed.data;
    await prismaClient().signal.upsert({
      where: { decisionId: payload.decisionId },
      update: {
        responseJson: payload.payload ?? {},
        action: payload.action,
      },
      create: {
        decisionId: payload.decisionId,
        signalId: payload.signalId,
        decisionKey: `${payload.strategyId}:${payload.symbol}:${payload.timeframe}:${payload.barCloseTimeUtc}`,
        strategyId: payload.strategyId,
        strategyVersion: payload.strategyVersion,
        modelVersion: payload.modelVersion,
        symbol: payload.symbol,
        timeframe: payload.timeframe,
        action: payload.action,
        barCloseTimeUtc: new Date(payload.barCloseTimeUtc),
        evaluatedAtUtc: new Date(payload.evaluatedAtUtc),
        requestJson: {},
        responseJson: payload.payload ?? {},
      },
    });

    recordFileLog({
      category: "audit",
      level: "info",
      event: "signal_logged",
      message: "Signal decision persisted",
      context: {
        decisionId: payload.decisionId,
        signalId: payload.signalId,
        strategyId: payload.strategyId,
        strategyVersion: payload.strategyVersion,
        symbol: payload.symbol,
        timeframe: payload.timeframe,
        action: payload.action,
      },
    });

    return { ok: true };
  });

  app.post("/log-rejected-signal", async (req, reply) => {
    const parsed = logRejectedSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    await prismaClient().rejectedSignal.create({
      data: {
        decisionId: parsed.data.decisionId,
        signalId: parsed.data.signalId,
        strategyId: parsed.data.strategyId,
        strategyVersion: parsed.data.strategyVersion,
        symbol: parsed.data.symbol,
        timeframe: parsed.data.timeframe,
        reasonCode: parsed.data.reasonCode,
        detailsJson: parsed.data.payload ?? {},
      },
    });

    recordFileLog({
      category: "audit",
      level: "info",
      event: "rejected_signal_logged",
      message: "Rejected signal persisted",
      context: {
        decisionId: parsed.data.decisionId,
        signalId: parsed.data.signalId ?? null,
        strategyId: parsed.data.strategyId,
        strategyVersion: parsed.data.strategyVersion,
        symbol: parsed.data.symbol,
        timeframe: parsed.data.timeframe,
        reasonCode: parsed.data.reasonCode,
      },
    });

    return { ok: true };
  });

  app.post("/log-trade", async (req, reply) => {
    const parsed = logTradeSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    await prismaClient().trade.upsert({
      where: { tradeId: parsed.data.tradeId },
      update: {
        status: parsed.data.status,
        closeReason: parsed.data.closeReason,
        spread: parsed.data.spread,
        slippage: parsed.data.slippage,
        commission: parsed.data.commission,
        swap: parsed.data.swap,
      },
      create: parsed.data,
    });

    recordFileLog({
      category: "audit",
      level: "info",
      event: "trade_logged",
      message: "Trade persisted",
      context: {
        tradeId: parsed.data.tradeId,
        decisionId: parsed.data.decisionId ?? null,
        signalId: parsed.data.signalId ?? null,
        strategyId: parsed.data.strategyId,
        strategyVersion: parsed.data.strategyVersion,
        symbol: parsed.data.symbol,
        side: parsed.data.side,
        status: parsed.data.status,
      },
    });

    return { ok: true };
  });
}
