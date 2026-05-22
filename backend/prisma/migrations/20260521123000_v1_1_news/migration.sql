-- CreateTable
CREATE TABLE "NewsEvent" (
    "newsEventId" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "providerEventId" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "countryCode" TEXT,
    "currencyCode" TEXT,
    "severity" TEXT NOT NULL,
    "scheduledAtUtc" TIMESTAMP(3) NOT NULL,
    "forecastValue" DOUBLE PRECISION,
    "previousValue" DOUBLE PRECISION,
    "actualValue" DOUBLE PRECISION,
    "status" TEXT NOT NULL,
    "rawJson" JSONB NOT NULL,
    "normalizedJson" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "NewsEvent_pkey" PRIMARY KEY ("newsEventId")
);

-- CreateTable
CREATE TABLE "NewsProviderStatus" (
    "provider" TEXT NOT NULL,
    "lastSuccessfulSyncUtc" TIMESTAMP(3),
    "lastAttemptedSyncUtc" TIMESTAMP(3) NOT NULL,
    "freshnessState" TEXT NOT NULL,
    "failureReason" TEXT,
    "budgetUsed" INTEGER,
    "budgetLimit" INTEGER,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "NewsProviderStatus_pkey" PRIMARY KEY ("provider")
);

-- CreateTable
CREATE TABLE "NewsGuardWindow" (
    "guardWindowId" TEXT NOT NULL,
    "newsEventId" TEXT NOT NULL,
    "symbolScope" TEXT NOT NULL,
    "currencyScope" TEXT,
    "policyAction" TEXT NOT NULL,
    "startsAtUtc" TIMESTAMP(3) NOT NULL,
    "endsAtUtc" TIMESTAMP(3) NOT NULL,
    "severity" TEXT NOT NULL,
    "reasonCode" TEXT NOT NULL,
    "metadataJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "NewsGuardWindow_pkey" PRIMARY KEY ("guardWindowId")
);

-- CreateIndex
CREATE UNIQUE INDEX "NewsEvent_provider_providerEventId_key" ON "NewsEvent"("provider", "providerEventId");

-- CreateIndex
CREATE INDEX "NewsEvent_scheduledAtUtc_idx" ON "NewsEvent"("scheduledAtUtc");

-- CreateIndex
CREATE INDEX "NewsEvent_currencyCode_scheduledAtUtc_idx" ON "NewsEvent"("currencyCode", "scheduledAtUtc");

-- CreateIndex
CREATE UNIQUE INDEX "NewsGuardWindow_newsEventId_symbolScope_policyAction_key" ON "NewsGuardWindow"("newsEventId", "symbolScope", "policyAction");

-- CreateIndex
CREATE INDEX "NewsGuardWindow_symbolScope_startsAtUtc_endsAtUtc_idx" ON "NewsGuardWindow"("symbolScope", "startsAtUtc", "endsAtUtc");

-- CreateIndex
CREATE INDEX "NewsGuardWindow_startsAtUtc_endsAtUtc_idx" ON "NewsGuardWindow"("startsAtUtc", "endsAtUtc");

-- AddForeignKey
ALTER TABLE "NewsGuardWindow" ADD CONSTRAINT "NewsGuardWindow_newsEventId_fkey" FOREIGN KEY ("newsEventId") REFERENCES "NewsEvent"("newsEventId") ON DELETE CASCADE ON UPDATE CASCADE;
