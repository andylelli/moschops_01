import { prismaClient } from "./prisma";

export type StrategyRuntimeConfig = {
  aiThresholds: {
    full: number;
    half: number;
  };
  aiMandatory: boolean;
  trainingDefaults: {
    datasetProfile: string;
    horizonBars: number;
    cvFolds: number;
    calibration: string;
    threshold: number;
    includeMacro: boolean;
    includeNewsWindows: boolean;
    includeSessionFeatures: boolean;
    enableClassWeights: boolean;
  };
};

export type StrategyRuntimeProfile = {
  strategyId: string;
  strategyVersion: string;
  riskProfile: string;
  source: "default" | "database";
  createdAt: string | null;
  config: StrategyRuntimeConfig;
};

const DEFAULT_CONFIG: StrategyRuntimeConfig = {
  aiThresholds: {
    full: 0.65,
    half: 0.55,
  },
  aiMandatory: false,
  trainingDefaults: {
    datasetProfile: "rolling-90d",
    horizonBars: 6,
    cvFolds: 5,
    calibration: "isotonic",
    threshold: 0.62,
    includeMacro: true,
    includeNewsWindows: true,
    includeSessionFeatures: true,
    enableClassWeights: true,
  },
};

function asNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  return fallback;
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  return fallback;
}

function asString(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }

  return fallback;
}

function mergeRuntimeConfig(configJson: unknown): StrategyRuntimeConfig {
  if (!configJson || typeof configJson !== "object") {
    return DEFAULT_CONFIG;
  }

  const candidate = configJson as Record<string, unknown>;
  const candidateThresholds =
    candidate.aiThresholds && typeof candidate.aiThresholds === "object"
      ? (candidate.aiThresholds as Record<string, unknown>)
      : {};
  const candidateTrainingDefaults =
    candidate.trainingDefaults && typeof candidate.trainingDefaults === "object"
      ? (candidate.trainingDefaults as Record<string, unknown>)
      : {};

  return {
    aiThresholds: {
      full: asNumber(candidateThresholds.full, DEFAULT_CONFIG.aiThresholds.full),
      half: asNumber(candidateThresholds.half, DEFAULT_CONFIG.aiThresholds.half),
    },
    aiMandatory: asBoolean(candidate.aiMandatory, DEFAULT_CONFIG.aiMandatory),
    trainingDefaults: {
      datasetProfile: asString(candidateTrainingDefaults.datasetProfile, DEFAULT_CONFIG.trainingDefaults.datasetProfile),
      horizonBars: asNumber(candidateTrainingDefaults.horizonBars, DEFAULT_CONFIG.trainingDefaults.horizonBars),
      cvFolds: asNumber(candidateTrainingDefaults.cvFolds, DEFAULT_CONFIG.trainingDefaults.cvFolds),
      calibration: asString(candidateTrainingDefaults.calibration, DEFAULT_CONFIG.trainingDefaults.calibration),
      threshold: asNumber(candidateTrainingDefaults.threshold, DEFAULT_CONFIG.trainingDefaults.threshold),
      includeMacro: asBoolean(candidateTrainingDefaults.includeMacro, DEFAULT_CONFIG.trainingDefaults.includeMacro),
      includeNewsWindows: asBoolean(candidateTrainingDefaults.includeNewsWindows, DEFAULT_CONFIG.trainingDefaults.includeNewsWindows),
      includeSessionFeatures: asBoolean(
        candidateTrainingDefaults.includeSessionFeatures,
        DEFAULT_CONFIG.trainingDefaults.includeSessionFeatures,
      ),
      enableClassWeights: asBoolean(candidateTrainingDefaults.enableClassWeights, DEFAULT_CONFIG.trainingDefaults.enableClassWeights),
    },
  };
}

export function defaultStrategyRuntimeProfile(strategyId = "daily-breakout-5-10", strategyVersion = "1.0.0"): StrategyRuntimeProfile {
  return {
    strategyId,
    strategyVersion,
    riskProfile: "balanced",
    source: "default",
    createdAt: null,
    config: DEFAULT_CONFIG,
  };
}

export async function loadStrategyRuntimeProfile(
  strategyId: string,
  strategyVersion: string,
): Promise<StrategyRuntimeProfile> {
  const latest = await prismaClient().strategyConfig.findFirst({
    where: {
      strategyId,
      strategyVersion,
    },
    orderBy: {
      createdAt: "desc",
    },
  });

  if (!latest) {
    return defaultStrategyRuntimeProfile(strategyId, strategyVersion);
  }

  return {
    strategyId,
    strategyVersion,
    riskProfile: latest.riskProfile ?? "balanced",
    source: "database",
    createdAt: latest.createdAt.toISOString(),
    config: mergeRuntimeConfig(latest.configJson),
  };
}
