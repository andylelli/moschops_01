-- CreateEnum
CREATE TYPE "DecisionAction" AS ENUM ('BUY', 'SELL', 'HOLD', 'CLOSE', 'REDUCE');

-- CreateTable
CREATE TABLE "StrategyConfig" (
    "id" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "riskProfile" TEXT,
    "configJson" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "StrategyConfig_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ModelVersion" (
    "id" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "modelVersion" TEXT NOT NULL,
    "lifecycleState" TEXT NOT NULL,
    "featureSchemaHash" TEXT,
    "metadataJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ModelVersion_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Signal" (
    "id" TEXT NOT NULL,
    "decisionId" TEXT NOT NULL,
    "signalId" TEXT NOT NULL,
    "decisionKey" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "modelVersion" TEXT,
    "symbol" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL,
    "action" "DecisionAction" NOT NULL,
    "barCloseTimeUtc" TIMESTAMP(3) NOT NULL,
    "evaluatedAtUtc" TIMESTAMP(3) NOT NULL,
    "requestJson" JSONB NOT NULL,
    "responseJson" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Signal_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RejectedSignal" (
    "id" TEXT NOT NULL,
    "decisionId" TEXT NOT NULL,
    "signalId" TEXT,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL,
    "reasonCode" TEXT NOT NULL,
    "detailsJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RejectedSignal_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Feature" (
    "id" TEXT NOT NULL,
    "decisionId" TEXT NOT NULL,
    "featureHash" TEXT,
    "datasetVersion" TEXT,
    "featureJson" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Feature_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ModelPrediction" (
    "id" TEXT NOT NULL,
    "decisionId" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "modelVersion" TEXT NOT NULL,
    "predictionScore" DOUBLE PRECISION NOT NULL,
    "predictionClass" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ModelPrediction_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Trade" (
    "id" TEXT NOT NULL,
    "tradeId" TEXT NOT NULL,
    "decisionId" TEXT,
    "signalId" TEXT,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "side" TEXT NOT NULL,
    "volume" DOUBLE PRECISION NOT NULL,
    "entryPrice" DOUBLE PRECISION NOT NULL,
    "stopPrice" DOUBLE PRECISION,
    "takeProfitPrice" DOUBLE PRECISION,
    "spread" DOUBLE PRECISION,
    "slippage" DOUBLE PRECISION,
    "commission" DOUBLE PRECISION,
    "swap" DOUBLE PRECISION,
    "status" TEXT NOT NULL,
    "closeReason" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Trade_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Position" (
    "id" TEXT NOT NULL,
    "positionId" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "side" TEXT NOT NULL,
    "volume" DOUBLE PRECISION NOT NULL,
    "averagePrice" DOUBLE PRECISION NOT NULL,
    "stopPrice" DOUBLE PRECISION,
    "takeProfitPrice" DOUBLE PRECISION,
    "unrealizedPnl" DOUBLE PRECISION,
    "isOpen" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Position_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RiskEvent" (
    "id" TEXT NOT NULL,
    "decisionId" TEXT,
    "strategyId" TEXT,
    "eventType" TEXT NOT NULL,
    "reasonCode" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "detailsJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RiskEvent_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AccountSnapshot" (
    "id" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "equity" DOUBLE PRECISION,
    "balance" DOUBLE PRECISION,
    "marginUsed" DOUBLE PRECISION,
    "freeMargin" DOUBLE PRECISION,
    "openRisk" DOUBLE PRECISION,
    "snapshotJson" JSONB NOT NULL,
    "capturedAtUtc" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AccountSnapshot_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TrainingRun" (
    "id" TEXT NOT NULL,
    "trainingRunId" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "modelVersion" TEXT,
    "datasetVersion" TEXT,
    "status" TEXT NOT NULL,
    "metricsJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "TrainingRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "OutcomeLabel" (
    "id" TEXT NOT NULL,
    "signalId" TEXT NOT NULL,
    "labelVersion" TEXT NOT NULL,
    "labelValue" INTEGER NOT NULL,
    "horizonBars" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OutcomeLabel_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PerformanceSnapshot" (
    "id" TEXT NOT NULL,
    "strategyId" TEXT NOT NULL,
    "strategyVersion" TEXT,
    "modelVersion" TEXT,
    "expectancy" DOUBLE PRECISION,
    "profitFactor" DOUBLE PRECISION,
    "sharpe" DOUBLE PRECISION,
    "maxDrawdown" DOUBLE PRECISION,
    "tradeCount" INTEGER,
    "snapshotJson" JSONB NOT NULL,
    "capturedAtUtc" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PerformanceSnapshot_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "OpenTradeSnapshot" (
    "id" TEXT NOT NULL,
    "accountId" TEXT,
    "strategyId" TEXT,
    "symbol" TEXT,
    "snapshotJson" JSONB NOT NULL,
    "capturedAtUtc" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OpenTradeSnapshot_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ModelVersion_modelVersion_key" ON "ModelVersion"("modelVersion");

-- CreateIndex
CREATE UNIQUE INDEX "Signal_decisionId_key" ON "Signal"("decisionId");

-- CreateIndex
CREATE UNIQUE INDEX "Signal_signalId_key" ON "Signal"("signalId");

-- CreateIndex
CREATE UNIQUE INDEX "Signal_decisionKey_key" ON "Signal"("decisionKey");

-- CreateIndex
CREATE UNIQUE INDEX "Trade_tradeId_key" ON "Trade"("tradeId");

-- CreateIndex
CREATE UNIQUE INDEX "Position_positionId_key" ON "Position"("positionId");

-- CreateIndex
CREATE UNIQUE INDEX "TrainingRun_trainingRunId_key" ON "TrainingRun"("trainingRunId");
