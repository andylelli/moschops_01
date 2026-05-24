import type { FastifyInstance } from "fastify";
import type { Prisma } from "@prisma/client";
import { z } from "zod";
import { prismaClient } from "../services/prisma";
import {
  downloadHistoricalBars,
  type HistoricalTimeframe,
} from "../services/historical-data";

const timeframeSchema = z.enum(["M15", "H1", "H4", "D1"]);

const downloadRequestSchema = z.object({
  source: z.string().default("FMP"),
  symbol: z.string().min(3).max(20),
  timeframe: timeframeSchema,
  fromDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  toDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  replaceExisting: z.boolean().default(false),
  requestedBy: z.string().max(64).optional(),
});

const barsQuerySchema = z.object({
  source: z.string().default("FMP"),
  symbol: z.string().min(3).max(20),
  timeframe: timeframeSchema,
  fromDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  toDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  limit: z.coerce.number().int().min(1).max(2000).default(500),
});

const jobsQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

function asDateRange(fromDate: string, toDate: string): { from: Date; to: Date } {
  const from = new Date(`${fromDate}T00:00:00Z`);
  const to = new Date(`${toDate}T23:59:59.999Z`);

  if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
    throw new Error("Invalid date range");
  }

  if (from > to) {
    throw new Error("fromDate must be before or equal to toDate");
  }

  return { from, to };
}

export async function historicalDataRoutes(app: FastifyInstance): Promise<void> {
  app.post("/historical-data/download", async (req, reply) => {
    const parsed = downloadRequestSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const source = parsed.data.source.toUpperCase();
    const symbol = parsed.data.symbol.toUpperCase();

    let fromTo: { from: Date; to: Date };

    try {
      fromTo = asDateRange(parsed.data.fromDate, parsed.data.toDate);
    } catch (error) {
      return reply.status(400).send({
        error: {
          code: "INVALID_REQUEST",
          message: error instanceof Error ? error.message : "Invalid date range",
        },
      });
    }

    const job = await prismaClient().historicalDownloadJob.create({
      data: {
        source,
        symbol,
        timeframe: parsed.data.timeframe,
        fromDate: fromTo.from,
        toDate: fromTo.to,
        status: "RUNNING",
        requestedBy: parsed.data.requestedBy,
        requestedAtUtc: new Date(),
      },
    });

    try {
      const bars = await downloadHistoricalBars({
        symbol,
        timeframe: parsed.data.timeframe as HistoricalTimeframe,
        fromDate: parsed.data.fromDate,
        toDate: parsed.data.toDate,
      });

      if (parsed.data.replaceExisting) {
        await prismaClient().historicalBar.deleteMany({
          where: {
            source,
            symbol,
            timeframe: parsed.data.timeframe,
            barCloseTimeUtc: {
              gte: fromTo.from,
              lte: fromTo.to,
            },
          },
        });
      }

      const insertResult = await prismaClient().historicalBar.createMany({
        data: bars.map((bar) => ({
          source,
          symbol,
          timeframe: parsed.data.timeframe,
          barCloseTimeUtc: bar.barCloseTimeUtc,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
          volume: bar.volume,
          rawJson: bar.rawJson as Prisma.InputJsonValue,
        })),
        skipDuplicates: true,
      });

      const barsFetched = bars.length;
      const barsInserted = insertResult.count;
      const barsSkipped = Math.max(0, barsFetched - barsInserted);

      const completedJob = await prismaClient().historicalDownloadJob.update({
        where: { id: job.id },
        data: {
          status: "COMPLETED",
          completedAtUtc: new Date(),
          barsFetched,
          barsInserted,
          barsSkipped,
          metadataJson: {
            replaceExisting: parsed.data.replaceExisting,
          },
        },
      });

      return {
        job: {
          id: completedJob.id,
          status: completedJob.status,
          source: completedJob.source,
          symbol: completedJob.symbol,
          timeframe: completedJob.timeframe,
          fromDate: completedJob.fromDate.toISOString(),
          toDate: completedJob.toDate.toISOString(),
          barsFetched: completedJob.barsFetched,
          barsInserted: completedJob.barsInserted,
          barsSkipped: completedJob.barsSkipped,
          requestedAtUtc: completedJob.requestedAtUtc.toISOString(),
          completedAtUtc: completedJob.completedAtUtc?.toISOString() ?? null,
        },
      };
    } catch (error) {
      const failedJob = await prismaClient().historicalDownloadJob.update({
        where: { id: job.id },
        data: {
          status: "FAILED",
          completedAtUtc: new Date(),
          errorMessage: error instanceof Error ? error.message.slice(0, 1000) : "Historical data download failed",
        },
      });

      return reply.status(500).send({
        error: {
          code: "DOWNLOAD_FAILED",
          message: failedJob.errorMessage ?? "Historical data download failed",
        },
        jobId: failedJob.id,
      });
    }
  });

  app.get("/historical-data/jobs", async (req, reply) => {
    const parsed = jobsQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const jobs = await prismaClient().historicalDownloadJob.findMany({
      orderBy: { requestedAtUtc: "desc" },
      take: parsed.data.limit,
    });

    return {
      count: jobs.length,
      items: jobs.map((job) => ({
        id: job.id,
        status: job.status,
        source: job.source,
        symbol: job.symbol,
        timeframe: job.timeframe,
        fromDate: job.fromDate.toISOString(),
        toDate: job.toDate.toISOString(),
        barsFetched: job.barsFetched,
        barsInserted: job.barsInserted,
        barsSkipped: job.barsSkipped,
        errorMessage: job.errorMessage,
        requestedAtUtc: job.requestedAtUtc.toISOString(),
        completedAtUtc: job.completedAtUtc?.toISOString() ?? null,
      })),
    };
  });

  app.get("/historical-data/bars", async (req, reply) => {
    const parsed = barsQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
    }

    const rangeStart = parsed.data.fromDate ? new Date(`${parsed.data.fromDate}T00:00:00Z`) : undefined;
    const rangeEnd = parsed.data.toDate ? new Date(`${parsed.data.toDate}T23:59:59.999Z`) : undefined;

    const bars = await prismaClient().historicalBar.findMany({
      where: {
        source: parsed.data.source.toUpperCase(),
        symbol: parsed.data.symbol.toUpperCase(),
        timeframe: parsed.data.timeframe,
        ...(rangeStart || rangeEnd
          ? {
              barCloseTimeUtc: {
                ...(rangeStart ? { gte: rangeStart } : {}),
                ...(rangeEnd ? { lte: rangeEnd } : {}),
              },
            }
          : {}),
      },
      orderBy: { barCloseTimeUtc: "desc" },
      take: parsed.data.limit,
    });

    return {
      count: bars.length,
      items: bars.map((bar) => ({
        id: bar.id,
        source: bar.source,
        symbol: bar.symbol,
        timeframe: bar.timeframe,
        barCloseTimeUtc: bar.barCloseTimeUtc.toISOString(),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume,
      })),
    };
  });
}
