-- CreateEnum
CREATE TYPE "NewsFreshnessState" AS ENUM ('FRESH', 'DEGRADED', 'STALE', 'DOWN');

-- CreateEnum
CREATE TYPE "NewsPolicyAction" AS ENUM ('BLOCK_NEW', 'REDUCE', 'ALLOW');

-- CreateTable
CREATE TABLE "news_events" (
    "newsEventId" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "providerEventId" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "countryCode" TEXT,
    "currencyCode" TEXT,
    "severity" TEXT NOT NULL,
    "scheduledAtUtc" TIMESTAMP(3) NOT NULL,
    "forecastValue" TEXT,
    "previousValue" TEXT,
    "actualValue" TEXT,
    "status" TEXT NOT NULL,
    "rawJson" JSONB NOT NULL,
    "normalizedJson" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "news_events_pkey" PRIMARY KEY ("newsEventId")
);

-- CreateTable
CREATE TABLE "news_provider_status" (
    "provider" TEXT NOT NULL,
    "lastSuccessfulSyncUtc" TIMESTAMP(3),
    "lastAttemptedSyncUtc" TIMESTAMP(3),
    "freshnessState" "NewsFreshnessState" NOT NULL DEFAULT 'DOWN',
    "failureReason" TEXT,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "news_provider_status_pkey" PRIMARY KEY ("provider")
);

-- CreateTable
CREATE TABLE "news_guard_windows" (
    "guardWindowId" TEXT NOT NULL,
    "newsEventId" TEXT NOT NULL,
    "symbolScope" TEXT,
    "currencyScope" TEXT,
    "policyAction" "NewsPolicyAction" NOT NULL,
    "startsAtUtc" TIMESTAMP(3) NOT NULL,
    "endsAtUtc" TIMESTAMP(3) NOT NULL,
    "severity" TEXT NOT NULL,
    "reasonCode" TEXT NOT NULL,
    "metadataJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "news_guard_windows_pkey" PRIMARY KEY ("guardWindowId")
);

-- CreateIndex
CREATE UNIQUE INDEX "news_events_provider_providerEventId_key" ON "news_events"("provider", "providerEventId");

-- CreateIndex
CREATE INDEX "news_events_scheduledAtUtc_idx" ON "news_events"("scheduledAtUtc");

-- CreateIndex
CREATE INDEX "news_guard_windows_startsAtUtc_idx" ON "news_guard_windows"("startsAtUtc");

-- CreateIndex
CREATE INDEX "news_guard_windows_endsAtUtc_idx" ON "news_guard_windows"("endsAtUtc");

-- AddForeignKey
ALTER TABLE "news_guard_windows" ADD CONSTRAINT "news_guard_windows_newsEventId_fkey" FOREIGN KEY ("newsEventId") REFERENCES "news_events"("newsEventId") ON DELETE CASCADE ON UPDATE CASCADE;
