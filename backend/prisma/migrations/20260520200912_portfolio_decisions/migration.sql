-- CreateTable
CREATE TABLE "PortfolioDecision" (
    "portfolioDecisionId" TEXT NOT NULL,
    "requestHash" TEXT NOT NULL,
    "accountId" TEXT NOT NULL,
    "requestJson" JSONB NOT NULL,
    "approvedPlans" TEXT[],
    "rejectedPlans" JSONB NOT NULL,
    "remainingRiskBudget" DOUBLE PRECISION NOT NULL,
    "remainingTradeSlots" INTEGER NOT NULL,
    "evaluatedAtUtc" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PortfolioDecision_pkey" PRIMARY KEY ("portfolioDecisionId")
);

-- CreateTable
CREATE TABLE "PortfolioDecisionItem" (
    "id" TEXT NOT NULL,
    "portfolioDecisionId" TEXT NOT NULL,
    "decisionId" TEXT NOT NULL,
    "approved" BOOLEAN NOT NULL,
    "reasonCodes" TEXT[],
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PortfolioDecisionItem_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "PortfolioDecision_requestHash_key" ON "PortfolioDecision"("requestHash");

-- AddForeignKey
ALTER TABLE "PortfolioDecisionItem" ADD CONSTRAINT "PortfolioDecisionItem_portfolioDecisionId_fkey" FOREIGN KEY ("portfolioDecisionId") REFERENCES "PortfolioDecision"("portfolioDecisionId") ON DELETE CASCADE ON UPDATE CASCADE;
