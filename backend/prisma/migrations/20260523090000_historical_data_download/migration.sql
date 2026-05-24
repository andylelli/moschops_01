-- CreateTable
CREATE TABLE "HistoricalDownloadJob" (
    "id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL,
    "fromDate" TIMESTAMP(3) NOT NULL,
    "toDate" TIMESTAMP(3) NOT NULL,
    "status" TEXT NOT NULL,
    "requestedBy" TEXT,
    "requestedAtUtc" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completedAtUtc" TIMESTAMP(3),
    "barsFetched" INTEGER NOT NULL DEFAULT 0,
    "barsInserted" INTEGER NOT NULL DEFAULT 0,
    "barsSkipped" INTEGER NOT NULL DEFAULT 0,
    "errorMessage" TEXT,
    "metadataJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "HistoricalDownloadJob_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "HistoricalBar" (
    "id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "symbol" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL,
    "barCloseTimeUtc" TIMESTAMP(3) NOT NULL,
    "open" DOUBLE PRECISION NOT NULL,
    "high" DOUBLE PRECISION NOT NULL,
    "low" DOUBLE PRECISION NOT NULL,
    "close" DOUBLE PRECISION NOT NULL,
    "volume" DOUBLE PRECISION,
    "rawJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "HistoricalBar_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "HistoricalDownloadJob_symbol_timeframe_requestedAtUtc_idx" ON "HistoricalDownloadJob"("symbol", "timeframe", "requestedAtUtc");

-- CreateIndex
CREATE INDEX "HistoricalDownloadJob_status_requestedAtUtc_idx" ON "HistoricalDownloadJob"("status", "requestedAtUtc");

-- CreateIndex
CREATE UNIQUE INDEX "HistoricalBar_source_symbol_timeframe_barCloseTimeUtc_key" ON "HistoricalBar"("source", "symbol", "timeframe", "barCloseTimeUtc");

-- CreateIndex
CREATE INDEX "HistoricalBar_symbol_timeframe_barCloseTimeUtc_idx" ON "HistoricalBar"("symbol", "timeframe", "barCloseTimeUtc");
