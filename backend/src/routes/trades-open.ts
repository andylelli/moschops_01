import type { FastifyInstance } from "fastify";
import { z } from "zod";
import { prismaClient } from "../services/prisma";

const openTradesSchema = z.object({
  accountId: z.string().optional(),
  strategyId: z.string().optional(),
  symbol: z.string().optional(),
  capturedAtUtc: z.string(),
  payload: z.any(),
});

export async function openTradesRoutes(app: FastifyInstance): Promise<void> {
  app.post("/trades/open", async (req, reply) => {
    const parsed = openTradesSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    await prismaClient().openTradeSnapshot.create({
      data: {
        accountId: parsed.data.accountId,
        strategyId: parsed.data.strategyId,
        symbol: parsed.data.symbol,
        capturedAtUtc: new Date(parsed.data.capturedAtUtc),
        snapshotJson: parsed.data.payload,
      },
    });

    return { ok: true };
  });

  app.get("/trades/open", async () => {
    const snapshots = await prismaClient().openTradeSnapshot.findMany({
      orderBy: { capturedAtUtc: "desc" },
      take: 100,
    });

    return {
      count: snapshots.length,
      items: snapshots,
    };
  });
}
