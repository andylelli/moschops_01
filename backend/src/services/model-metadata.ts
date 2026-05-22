import fs from "node:fs";
import path from "node:path";
import type { FastifyBaseLogger } from "fastify";
import { Prisma } from "@prisma/client";
import { prismaClient } from "./prisma";

interface TrainingReport {
  generatedAtUtc?: string;
  model?: string;
  metrics?: Record<string, unknown>;
}

function resolveModelPath(): string {
  return path.resolve(process.cwd(), "../models/daily_breakout_model.onnx");
}

function resolveTrainingReportPath(): string {
  return path.resolve(process.cwd(), "../models/training_report.json");
}

function readTrainingReport(): TrainingReport | null {
  const reportPath = resolveTrainingReportPath();
  if (!fs.existsSync(reportPath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(reportPath, "utf8");
    const parsed = JSON.parse(raw) as TrainingReport;
    return parsed;
  } catch {
    return null;
  }
}

function buildSeedModelVersion(report: TrainingReport | null): string {
  const modelName = typeof report?.model === "string" && report.model ? report.model : "onnx";
  const generatedDate =
    typeof report?.generatedAtUtc === "string" && report.generatedAtUtc
      ? report.generatedAtUtc.slice(0, 10)
      : new Date().toISOString().slice(0, 10);

  return `${modelName}-${generatedDate}`;
}

export async function ensureActiveModelVersionRecord(log?: FastifyBaseLogger): Promise<void> {
  const existing = await prismaClient().modelVersion.findFirst({
    orderBy: { createdAt: "desc" },
  });

  if (existing) {
    return;
  }

  const modelPath = resolveModelPath();
  if (!fs.existsSync(modelPath)) {
    log?.warn({ modelPath }, "model metadata seed skipped because ONNX artifact is missing");
    return;
  }

  const report = readTrainingReport();
  const modelVersion = buildSeedModelVersion(report);

  try {
    await prismaClient().modelVersion.create({
      data: {
        strategyId: "daily-breakout-5-10",
        strategyVersion: "1.0.0",
        modelVersion,
        lifecycleState: "ACTIVE",
        featureSchemaHash: null,
        metadataJson: {
          source: "bootstrap-seed",
          onnxPath: modelPath,
          trainingReportPath: resolveTrainingReportPath(),
          generatedAtUtc: report?.generatedAtUtc ?? null,
          modelType: report?.model ?? null,
          metrics: (report?.metrics ?? null) as Prisma.InputJsonValue | null,
        },
      },
    });

    log?.info({ modelVersion }, "seeded active model metadata record");
  } catch (error) {
    if (
      error instanceof Prisma.PrismaClientKnownRequestError &&
      error.code === "P2002"
    ) {
      return;
    }

    throw error;
  }
}
