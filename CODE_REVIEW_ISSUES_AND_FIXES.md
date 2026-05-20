# Code Review - Critical Issues & Fixes
## v1.0 Actionable Remediation Guide

**Status:** Issues identified from 5-pass review  
**Target:** v1.0.1 (Production Stabilization)

---

## ISSUE #1 (CRITICAL): Inference Feature Mismatch
### Location: backend/src/routes/signal.ts (lines 60-66)
### Severity: 🔴 MEDIUM (Logic Broken)

**Problem:**
The signal route generates 5 feature values for ONNX inference, but they don't match the training features. Specifically:
- **Training feature #2**: "volatility" = rolling standard deviation of returns
- **Runtime feature #2**: `atr20_1` = average true range

ATR and volatility are NOT equivalent. This causes model predictions to be meaningless.

**Current Code:**
```typescript
// signal.ts lines 60-66
const inferenceFeatures = [
  input.marketSnapshot.close1 - input.marketSnapshot.sma200_1,  // ✅ trend_strength (correct)
  input.marketSnapshot.atr20_1,                                   // ❌ NOT volatility! (WRONG)
  (input.marketSnapshot.spreadPrice ?? 0) / Math.max(input.marketSnapshot.atr20_1, 0.000001),  // ✅ spread_atr (OK)
  input.marketSnapshot.close1 - input.marketSnapshot.highestHigh55,  // ✅ breakout_distance (correct)
  input.marketSnapshot.close1 - input.marketSnapshot.sma100_1,   // ✅ momentum (correct)
];
```

**Training Code (for comparison):**
```python
# training/train_walk_forward.py lines 33-34
df = pd.DataFrame({
    "trend_strength": rng.normal(0, 1, rows),
    "volatility": rng.uniform(0.2, 2.5, rows),  # ← Uniform distribution, NOT ATR
    ...
})
```

**Why It Matters:**
- Model learned patterns with volatility in range [0.2, 2.5]
- Runtime sends ATR values in potentially different range
- Model applies learned coefficients to wrong feature distribution
- Predictions will be statistically invalid

**Fix:**
Option A: **Compute actual volatility** (recommended)
```typescript
// Add to market snapshot calculation or accept as input from EA
// Compute rolling volatility (std dev of log returns)
const computeVolatility = (closes: number[]): number => {
  if (closes.length < 2) return 0;
  const returns = [];
  for (let i = 1; i < closes.length; i++) {
    returns.push(Math.log(closes[i] / closes[i - 1]));
  }
  const mean = returns.reduce((a, b) => a + b) / returns.length;
  const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2)) / returns.length;
  return Math.sqrt(variance);
};

const inferenceFeatures = [
  input.marketSnapshot.close1 - input.marketSnapshot.sma200_1,
  computeVolatility([...recent_closes]),  // ← Actual volatility
  (input.marketSnapshot.spreadPrice ?? 0) / Math.max(input.marketSnapshot.atr20_1, 0.000001),
  input.marketSnapshot.close1 - input.marketSnapshot.highestHigh55,
  input.marketSnapshot.close1 - input.marketSnapshot.sma100_1,
];
```

Option B: **Update training to use ATR** (simpler short-term)
```python
# training/train_walk_forward.py
df = pd.DataFrame({
    "trend_strength": rng.normal(0, 1, rows),
    "volatility_atr": rng.uniform(5, 50, rows),  # ← ATR-like range, matches runtime
    ...
})
# Then retrain model and export ONNX
```

**Recommended:** Option A (compute actual volatility). Ensures model receives feature in intended distribution.

**Acceptance Criteria:**
- [ ] Feature array values match training distribution
- [ ] Training notebook documents feature definitions
- [ ] Integration test verifies feature ranges
- [ ] Model performance validated on same feature set

---

## ISSUE #2 (HIGH): Missing Integration Test Coverage
### Location: backend/test/integration.test.ts
### Severity: 🔴 HIGH (6/9 Tests Failing)

**Problem:**
Integration tests have 6 failing tests out of 9. These test critical paths:
- Signal persistence to DB
- Portfolio risk decisions
- Risk-check endpoint validation
- Idempotent signal writes (retry safety)
- End-to-end flow

**Current Status:**
```
Test Files  2 failed (2)
Tests  6 failed | 3 passed (9)
```

**Passing Tests:**
✅ health endpoint returns 200 with telemetry
✅ evaluates portfolio plans with risk caps
✅ health endpoint reports DB connectivity

**Failing Tests:**
❌ signal → DB write → queryable decision trace
❌ portfolio evaluation persists risk decisions
❌ risk-check endpoint validates decisions
❌ idempotent signal writes (same decisionId returns same result)
❌ end-to-end scenario: signal → portfolio check → decision

**Root Cause:**
Zod schema validation issues; payloads missing required fields (strategyVersion, timeframe, etc.)

**Fix:**
```typescript
// backend/test/integration.test.ts - COMPLETE TEST SUITE

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { buildApp } from "../src/app";
import { prismaClient } from "../src/services/prisma";
import type { FastifyInstance } from "fastify";

describe("Phase 3 - Persistence & Audit Logging Integration Tests", () => {
  let app: FastifyInstance;

  beforeAll(async () => {
    app = buildApp();
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
  });

  // Test 1: Signal persisted and queryable
  it("signal → DB write → queryable decision trace", async () => {
    const decisionId = `test-${Date.now()}-1`;
    const response = await app.inject({
      method: "POST",
      url: "/signal",
      payload: {
        decisionId,
        strategyId: "daily-breakout-v1",
        strategyVersion: "1.0.0",
        modelVersion: "logreg-v1",
        symbol: "EURUSD",
        timeframe: "D1",
        barCloseTimeUtc: new Date().toISOString(),
        marketSnapshot: {
          symbol: "EURUSD",
          timeframe: "D1",
          barCloseTimeUtc: new Date().toISOString(),
          close1: 1.1050,
          sma100_1: 1.1000,
          sma200_1: 1.0950,
          highestHigh55: 1.1100,
          lowestLow55: 1.0900,
          atr20_1: 0.0050,
          spreadPrice: 0.0002,
        },
        accountSnapshot: {
          accountId: "demo-account-1",
          equity: 10000,
          balance: 10000,
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0.00,
          weeklyLossPct: 0.00,
        },
      },
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.decisionId).toBe(decisionId);
    expect(body.action).toMatch(/^(BUY|SELL|HOLD)$/);
    expect(body.riskDecision).toMatch(/^(APPROVED|VETOED)$/);

    // Verify DB write
    const signal = await prismaClient().signal.findUnique({
      where: { decisionId },
    });
    expect(signal).toBeDefined();
    expect(signal?.action).toBe(body.action);
    expect(signal?.strategyId).toBe("daily-breakout-v1");
  });

  // Test 2: Portfolio evaluation persists decisions
  it("portfolio evaluation persists risk decisions", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/portfolio/evaluate",
      payload: {
        accountSnapshot: {
          accountId: "demo-account-1",
          openRisk: 0.01,
          openTrades: 1,
          dailyLossPct: 0.00,
          weeklyLossPct: 0.00,
        },
        plans: [
          {
            decisionId: `portfolio-test-${Date.now()}`,
            strategyId: "daily-breakout-v1",
            symbol: "GBPUSD",
            proposedRiskPct: 0.02,
          },
        ],
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
      },
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.approvedPlans).toBeDefined();
    expect(body.rejectedPlans).toBeDefined();
    expect(body.remainingRiskBudget).toBeLessThanOrEqual(0.04);
  });

  // Test 3: Risk-check endpoint validates decisions
  it("risk-check endpoint validates decisions", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/risk-check",
      payload: {
        decisionId: `risk-check-${Date.now()}`,
        strategyId: "daily-breakout-v1",
        symbol: "EURUSD",
        proposedRiskPct: 0.005,
        proposedOpenTrades: 1,
        maxOpenRisk: 0.04,
        maxOpenTrades: 6,
        accountSnapshot: {
          accountId: "demo-account-1",
          openRisk: 0.01,
          openTrades: 2,
          dailyLossPct: 0.005,
          weeklyLossPct: 0.01,
        },
      },
    });

    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.body);
    expect(body.approved).toBeDefined();
    expect(typeof body.approved).toBe("boolean");
  });

  // Test 4: Idempotent signal writes
  it("idempotent signal writes (same decisionId returns same result)", async () => {
    const decisionId = `idempotent-${Date.now()}`;
    const payload = {
      decisionId,
      strategyId: "daily-breakout-v1",
      strategyVersion: "1.0.0",
      symbol: "EURUSD",
      timeframe: "D1",
      barCloseTimeUtc: new Date().toISOString(),
      marketSnapshot: {
        symbol: "EURUSD",
        timeframe: "D1",
        barCloseTimeUtc: new Date().toISOString(),
        close1: 1.1050,
        sma100_1: 1.1000,
        sma200_1: 1.0950,
        highestHigh55: 1.1100,
        lowestLow55: 1.0900,
        atr20_1: 0.0050,
      },
      accountSnapshot: {
        accountId: "demo-account-1",
        equity: 10000,
        openRisk: 0.01,
        openTrades: 1,
      },
    };

    // First request
    const response1 = await app.inject({
      method: "POST",
      url: "/signal",
      payload,
    });
    const body1 = JSON.parse(response1.body);

    // Second request (same decisionId)
    const response2 = await app.inject({
      method: "POST",
      url: "/signal",
      payload,
    });
    const body2 = JSON.parse(response2.body);

    // Results should be identical
    expect(body1.action).toBe(body2.action);
    expect(body1.riskDecision).toBe(body2.riskDecision);
    expect(body1.reasonCodes).toEqual(body2.reasonCodes);

    // Only one signal should be in DB
    const signals = await prismaClient().signal.findMany({
      where: { decisionId },
    });
    expect(signals.length).toBe(1);
  });

  // Test 5: End-to-end scenario
  it("end-to-end scenario: signal → portfolio check → decision", async () => {
    // Step 1: Get signal
    const signalRes = await app.inject({
      method: "POST",
      url: "/signal",
      payload: {
        decisionId: `e2e-${Date.now()}`,
        strategyId: "daily-breakout-v1",
        strategyVersion: "1.0.0",
        symbol: "EURUSD",
        timeframe: "D1",
        barCloseTimeUtc: new Date().toISOString(),
        marketSnapshot: {
          symbol: "EURUSD",
          timeframe: "D1",
          barCloseTimeUtc: new Date().toISOString(),
          close1: 1.1050,
          sma100_1: 1.1000,
          sma200_1: 1.0950,
          highestHigh55: 1.1100,
          lowestLow55: 1.0900,
          atr20_1: 0.0050,
        },
        accountSnapshot: {
          accountId: "demo-account-1",
          equity: 10000,
          openRisk: 0.01,
          openTrades: 1,
        },
      },
    });
    expect(signalRes.statusCode).toBe(200);
    const signal = JSON.parse(signalRes.body);

    // Step 2: Check portfolio if signal approved
    if (signal.riskDecision === "APPROVED") {
      const portfolioRes = await app.inject({
        method: "POST",
        url: "/portfolio/evaluate",
        payload: {
          accountSnapshot: {
            accountId: "demo-account-1",
            openRisk: 0.01,
            openTrades: 1,
          },
          plans: [
            {
              decisionId: signal.decisionId,
              strategyId: "daily-breakout-v1",
              symbol: "EURUSD",
              proposedRiskPct: 0.005,
            },
          ],
          maxOpenRisk: 0.04,
          maxOpenTrades: 6,
        },
      });
      expect(portfolioRes.statusCode).toBe(200);
      const portfolio = JSON.parse(portfolioRes.body);
      expect(portfolio.approvedPlans || portfolio.rejectedPlans).toBeDefined();
    }
  });
});
```

**Acceptance Criteria:**
- [ ] All 9 tests pass (`npm run test`)
- [ ] Database persists signal and portfolio decisions
- [ ] Idempotent retries return same result
- [ ] Error scenarios return 400 with clear error codes
- [ ] Test suite covers happy path + veto scenarios

---

## ISSUE #3 (HIGH): Silent Model Load Failure
### Location: backend/src/services/model-inference.ts (lines 8-18)
### Severity: 🟡 MEDIUM (Observability Gap)

**Problem:**
If ONNX model file is missing or corrupted, `inferScore()` silently returns `null`. This causes:
1. No error logged
2. AI layer degraded without operator awareness
3. Decisions made with undefined AI score, indistinguishable from "no model available"

**Current Code:**
```typescript
async function getSession(): Promise<ort.InferenceSession | null> {
  if (session) return session;

  const modelPath = path.resolve(process.cwd(), "../models/daily_breakout_model.onnx");
  if (!fs.existsSync(modelPath)) {
    return null;  // ← Silent failure; no logging
  }

  session = await ort.InferenceSession.create(modelPath);  // ← Could throw; not caught
  return session;
}
```

**Fix:**
```typescript
import fs from "node:fs";
import path from "node:path";
import * as ort from "onnxruntime-node";

let session: ort.InferenceSession | null = null;
let modelLoadError: Error | null = null;

async function getSession(): Promise<ort.InferenceSession | null> {
  if (session) {
    return session;
  }

  // Return null if we already tried and failed
  if (modelLoadError) {
    return null;
  }

  const modelPath = path.resolve(process.cwd(), "../models/daily_breakout_model.onnx");

  // Check file exists
  if (!fs.existsSync(modelPath)) {
    const error = new Error(`Model file not found: ${modelPath}`);
    modelLoadError = error;
    console.error("MODEL_LOAD_FAILED:", error.message);  // ← Explicit logging
    return null;
  }

  try {
    console.log("Loading ONNX model from:", modelPath);
    session = await ort.InferenceSession.create(modelPath);
    console.log("Model loaded successfully");
    return session;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    modelLoadError = err;
    console.error("MODEL_LOAD_FAILED:", {
      path: modelPath,
      error: err.message,
      stack: err.stack,
    });  // ← Full error context
    return null;
  }
}

export async function inferScore(features: number[]): Promise<number | null> {
  const active = await getSession();
  if (!active) {
    // Operator can distinguish: model unavailable vs. inference error
    if (modelLoadError) {
      console.warn("Inference skipped: model load failed. See MODEL_LOAD_FAILED logs.");
    }
    return null;
  }

  try {
    const inputName = active.inputNames[0];
    const outputName = active.outputNames[0];
    const tensor = new ort.Tensor("float32", Float32Array.from(features), [1, features.length]);
    const outputs = await active.run({ [inputName]: tensor });
    const out = outputs[outputName].data as Float32Array | number[];

    if (Array.isArray(out)) {
      return Number(out[0] ?? 0);
    }

    return Number(out[0] ?? 0);
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.error("INFERENCE_ERROR:", {
      error: err.message,
      features,
      stack: err.stack,
    });  // ← Inference failure logged
    return null;
  }
}
```

**Acceptance Criteria:**
- [ ] Model load errors logged with "MODEL_LOAD_FAILED" tag
- [ ] File not found case explicitly logged
- [ ] Inference errors logged with feature context
- [ ] Operators can enable model load tracing via LOG_LEVEL=debug

---

## ISSUE #4 (MEDIUM): Portfolio Endpoint - No Transaction
### Location: backend/src/routes/portfolio.ts (lines 30-70)
### Severity: 🟡 MEDIUM (Data Consistency Risk)

**Problem:**
Portfolio evaluation returns multiple approved plans but doesn't persist the decision atomically. If network fails after evaluation but before client receives response, approved plans lose context.

**Scenario:**
```
1. Client sends 5 plans to /portfolio/evaluate
2. Backend evaluates all 5; approves 3
3. Response starts: "approvedPlans": ["plan-1", "plan-2", "plan-3"]
4. Network packet lost mid-response
5. Client retries (doesn't know if first request succeeded)
6. Backend evaluates again; same 3 plans approved (or different due to state change)
7. Client confusion: Are there 3 or 6 approved plans now?
```

**Fix:**
Wrap decision in database transaction:

```typescript
export async function portfolioRoutes(app: FastifyInstance): Promise<void> {
  app.post("/portfolio/evaluate", async (req, reply) => {
    const parsed = portfolioSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.status(400).send({ 
        error: { code: "INVALID_REQUEST", message: parsed.error.message } 
      });
    }

    const body = parsed.data;
    
    // Check if this portfolio evaluation was already done (idempotency)
    const portfolioDecisionId = `portfolio-${body.accountSnapshot.accountId}-${Date.now()}`;
    
    try {
      // Start transaction
      const result = await prismaClient().$transaction(async (tx) => {
        // Create portfolio decision record first
        const portfolioDecision = await tx.portfolioDecision.create({
          data: {
            portfolioDecisionId,
            accountId: body.accountSnapshot.accountId,
            evaluatedAtUtc: new Date().toISOString(),
            requestJson: body,
            plansCount: body.plans.length,
          },
        });

        let runningOpenRisk = body.accountSnapshot.openRisk ?? 0;
        let runningOpenTrades = body.accountSnapshot.openTrades ?? 0;

        const approvedPlans: string[] = [];
        const rejectedPlans: Array<{ decisionId: string; reasonCodes: string[] }> = [];

        // Evaluate each plan
        for (const plan of body.plans) {
          const result = evaluateAccountLevelRisk({
            decisionId: plan.decisionId,
            strategyId: plan.strategyId,
            symbol: plan.symbol,
            proposedRiskPct: plan.proposedRiskPct,
            proposedOpenTrades: 1,
            maxOpenRisk: body.maxOpenRisk,
            maxOpenTrades: body.maxOpenTrades,
            accountSnapshot: {
              accountId: body.accountSnapshot.accountId,
              openRisk: runningOpenRisk,
              openTrades: runningOpenTrades,
              dailyLossPct: body.accountSnapshot.dailyLossPct,
              weeklyLossPct: body.accountSnapshot.weeklyLossPct,
            },
          });

          if (result.approved) {
            approvedPlans.push(plan.decisionId);
            runningOpenRisk += plan.proposedRiskPct;
            runningOpenTrades += 1;

            // Persist approval
            await tx.portfolioDecisionItem.create({
              data: {
                portfolioDecisionId,
                decisionId: plan.decisionId,
                approved: true,
                reasonCodes: [],
              },
            });
          } else {
            rejectedPlans.push({ 
              decisionId: plan.decisionId, 
              reasonCodes: result.vetoReasonCodes 
            });

            // Persist rejection
            await tx.portfolioDecisionItem.create({
              data: {
                portfolioDecisionId,
                decisionId: plan.decisionId,
                approved: false,
                reasonCodes: result.vetoReasonCodes,
              },
            });
          }
        }

        return {
          portfolioDecisionId,
          approvedPlans,
          rejectedPlans,
          remainingRiskBudget: Math.max(0, body.maxOpenRisk - runningOpenRisk),
          remainingTradeSlots: Math.max(0, body.maxOpenTrades - runningOpenTrades),
          evaluatedAtUtc: new Date().toISOString(),
        };
      });

      return result;
    } catch (error) {
      req.log.error({ error }, "portfolio evaluation failed");
      return reply.status(500).send({ 
        error: { 
          code: "PORTFOLIO_EVAL_FAILED", 
          portfolioDecisionId 
        } 
      });
    }
  });
}
```

**Schema additions (Prisma):**
```prisma
model PortfolioDecision {
  portfolioDecisionId String @id @default(cuid())
  accountId String
  evaluatedAtUtc DateTime
  requestJson Json
  plansCount Int
  items PortfolioDecisionItem[]
  createdAt DateTime @default(now())
}

model PortfolioDecisionItem {
  id String @id @default(cuid())
  portfolioDecisionId String
  decisionId String
  approved Boolean
  reasonCodes String[]
  portfolioDecision PortfolioDecision @relation(fields: [portfolioDecisionId], references: [portfolioDecisionId], onDelete: Cascade)
  createdAt DateTime @default(now())
}
```

**Acceptance Criteria:**
- [ ] Portfolio decisions persisted atomically
- [ ] All-or-nothing: if one item fails, all rolled back
- [ ] portfolioDecisionId returned for tracking
- [ ] Retry with same portfolioDecisionId returns cached result (idempotent)

---

## ISSUE #5 (MEDIUM): Configuration Hard-Coded
### Location: Multiple files (risk-engine.ts, signal.ts, portfolio.ts)
### Severity: 🟡 MEDIUM (Maintainability)

**Problem:**
Risk thresholds are hard-coded in multiple places:
- Max open risk: 0.04 (4 locations)
- Max open trades: 6 (3 locations)
- Spread/ATR ratio: 0.2 (1 location)
- AI score thresholds: 0.65, 0.55 (1 location)

Changes require code edits in multiple files; risk of inconsistency.

**Fix:**
Create config module:

```typescript
// backend/src/config/riskLimits.ts
/**
 * Risk control thresholds and limits
 * Source: docs/02-architecture/lld_v1.md § Risk Engine Controls
 */

export const RISK_LIMITS = {
  // Portfolio-level limits
  maxOpenRiskPct: 0.04,        // 4% max open risk
  maxOpenTrades: 6,             // Max 6 concurrent positions
  
  // Signal-level limits
  maxRiskPerTradePct: 0.005,    // 0.5% max per trade
  maxSpreadAtrRatio: 0.2,       // Spread ≤ 20% of ATR
  
  // AI thresholds
  aiScoreThresholds: {
    full: 0.65,   // score ≥ 0.65 → FULL sizing
    half: 0.55,   // score ∈ [0.55, 0.65) → HALF sizing
    skip: 0.0,    // score < 0.55 → SKIP (no trade)
  },
  
  // Daily/weekly loss limits
  dailyLossLimitPct: 0.03,      // 3% daily loss cap
  weeklyLossLimitPct: 0.06,     // 6% weekly loss cap
} as const;

/**
 * Validate thresholds consistency at app startup.
 * Ensures no configuration drift.
 */
export function validateRiskLimits(): void {
  const { aiScoreThresholds } = RISK_LIMITS;
  if (aiScoreThresholds.half >= aiScoreThresholds.full) {
    throw new Error("AI score half threshold must be < full threshold");
  }
  if (aiScoreThresholds.skip < 0 || aiScoreThresholds.full > 1) {
    throw new Error("AI score thresholds must be in [0, 1]");
  }
  console.log("✓ Risk limits validated");
}
```

**Usage in risk-engine.ts:**
```typescript
import { RISK_LIMITS } from "../config/riskLimits";

export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
  const reasons: string[] = [];
  const atr = input.marketSnapshot.atr20_1;
  const spread = input.marketSnapshot.spreadPrice ?? 0;

  if (atr <= 0) {
    reasons.push("INVALID_ATR");
  }

  // Use centralized config instead of hard-coded 0.2
  if (spread > 0 && atr > 0 && spread / atr > RISK_LIMITS.maxSpreadAtrRatio) {
    reasons.push("SPREAD_TOO_WIDE");
  }

  if ((input.accountSnapshot.openTrades ?? 0) >= RISK_LIMITS.maxOpenTrades) {
    reasons.push("MAX_OPEN_TRADES_REACHED");
  }

  if ((input.accountSnapshot.openRisk ?? 0) >= RISK_LIMITS.maxOpenRiskPct) {
    reasons.push("MAX_OPEN_RISK_REACHED");
  }

  return { approved: reasons.length === 0, reasonCodes: reasons };
}
```

**Usage in signal.ts:**
```typescript
import { RISK_LIMITS } from "../config/riskLimits";

// Lines 64-76
let sizeBucket: "FULL" | "HALF" | "SKIP" = "FULL";
if (typeof inferredScore === "number") {
  if (inferredScore >= RISK_LIMITS.aiScoreThresholds.full) {
    sizeBucket = "FULL";
  } else if (inferredScore >= RISK_LIMITS.aiScoreThresholds.half) {
    sizeBucket = "HALF";
    aiReasons.push("AI_HALF_SIZE");
  } else {
    sizeBucket = "SKIP";
    aiReasons.push("AI_SKIP");
  }
}
```

**Acceptance Criteria:**
- [ ] All thresholds moved to `src/config/riskLimits.ts`
- [ ] Validation function called in `app.ts` on startup
- [ ] All references updated (grep RISK_LIMITS returns > 10 hits)
- [ ] Config linked to documentation (comment points to LLD)

---

## ISSUE #6 (MEDIUM): Environment Variable Validation
### Location: backend/src/utils/env.ts
### Severity: 🟡 MEDIUM (Deployment Risk)

**Problem:**
Environment variables not validated at startup. Missing DATABASE_URL silently becomes `undefined`, causing cryptic Prisma errors later.

**Current Code:**
```typescript
export const env = {
  nodeEnv: process.env.NODE_ENV || "development",
  logLevel: process.env.LOG_LEVEL || "info",
  port: parseInt(process.env.PORT || "3000"),
  databaseUrl: process.env.DATABASE_URL,  // ← Undefined if not set
};
```

**Fix:**
```typescript
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  PORT: z.coerce.number().int().positive().default(3000),
  DATABASE_URL: z.string().url("Must be a valid PostgreSQL connection URL"),
});

export type Env = z.infer<typeof EnvSchema>;

function parseEnv(): Env {
  const result = EnvSchema.safeParse(process.env);

  if (!result.success) {
    console.error("❌ Invalid environment configuration:");
    result.error.errors.forEach((err) => {
      console.error(`  - ${err.path.join(".")}: ${err.message}`);
    });
    process.exit(1);  // ← Fail fast
  }

  console.log("✓ Environment configuration validated");
  return result.data;
}

export const env = parseEnv();
```

**Call in app.ts:**
```typescript
import { env } from "./utils/env";

export function buildApp(): FastifyInstance {
  const app = Fastify({
    logger: {
      level: env.LOG_LEVEL,  // ← Validated
      transport: env.NODE_ENV === "development" ? { target: "pino-pretty" } : undefined,
    },
  });

  // app setup...
  return app;
}
```

**Acceptance Criteria:**
- [ ] All required env vars validated at startup
- [ ] Missing vars cause immediate exit with clear error message
- [ ] Type safety for env values (no `any`)
- [ ] Documented in README.md

---

## ISSUE #7 (MEDIUM): JSDoc Documentation Missing
### Location: backend/src/services/risk-engine.ts
### Severity: 🟡 MEDIUM (Maintainability)

**Problem:**
Risk engine functions lack documentation. Threshold values appear magic; no rationale documented.

**Current Code:**
```typescript
export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
  const reasons: string[] = [];
  const atr = input.marketSnapshot.atr20_1;
  const spread = input.marketSnapshot.spreadPrice ?? 0;

  if (spread > 0 && atr > 0 && spread / atr > 0.2) {  // ← Why 0.2?
    reasons.push("SPREAD_TOO_WIDE");
  }
  // ...
}
```

**Fix:**
```typescript
/**
 * Evaluate signal-level risk controls.
 * 
 * Performs basic safety checks on individual trade signals before they reach
 * portfolio-level evaluation. All checks must pass for approval.
 *
 * @param input Signal evaluation request with market and account snapshots
 * @returns Risk decision indicating approval status and veto reason codes
 *
 * Constraints checked (fail-safe: any violation → VETOED):
 * 1. **ATR Validity**: ATR > 0 (ensures market is tradeable)
 *    - Reason: ATR ≤ 0 indicates no volatility; trade unsafe
 *    - Source: Market data validation
 *
 * 2. **Spread Guard**: spread / ATR ≤ 0.2 (spread < 20% of ATR)
 *    - Reason: Wide spreads consume risk budget; threshold = 20% of stop distance
 *    - Threshold Rationale: If stop = 50 pips, spread > 10 pips is considered too wide
 *    - Source: docs/02-architecture/lld_v1.md § Signal-Level Risk § Spread Guard
 *
 * 3. **Open Trades Limit**: openTrades < 6 (portfolio concentration)
 *    - Reason: Limit correlation risk; prevent over-leveraging
 *    - Threshold Rationale: 6 positions allows diversification without resource exhaustion
 *    - Source: docs/02-architecture/lld_v1.md § Portfolio Limits § Max Open Trades
 *
 * 4. **Open Risk Limit**: openRisk < 4% (account protection)
 *    - Reason: Prevent account blowout from cascade losses
 *    - Threshold Rationale: 4% = conservative limit for demo; ~1 losing trade before stop
 *    - Source: docs/02-architecture/lld_v1.md § Portfolio Limits § Max Open Risk
 *
 * @example
 * const decision = evaluateSignalLevelRisk({
 *   marketSnapshot: { atr20_1: 0.0050, spreadPrice: 0.0002, ... },
 *   accountSnapshot: { openTrades: 2, openRisk: 0.02, ... },
 *   ...
 * });
 * 
 * if (!decision.approved) {
 *   console.log("Trade vetoed:", decision.reasonCodes);
 *   // Output: ["SPREAD_TOO_WIDE"]
 * }
 *
 * @see evaluateAccountLevelRisk for portfolio-level checks
 * @see docs/02-architecture/lld_v1.md#risk-engine-controls for full spec
 */
export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
  const reasons: string[] = [];
  const atr = input.marketSnapshot.atr20_1;
  const spread = input.marketSnapshot.spreadPrice ?? 0;

  // ATR Validity Check
  if (atr <= 0) {
    reasons.push("INVALID_ATR");
  }

  // Spread Guard: spread/atr ratio must be ≤ 0.2 (20% of ATR)
  // Threshold: If ATR = 50 pips, allowed spread = 10 pips max
  if (spread > 0 && atr > 0 && spread / atr > 0.2) {
    reasons.push("SPREAD_TOO_WIDE");
  }

  // Open Trades Limit: must be < 6 positions
  // Rationale: Correlation risk limit; max 6 concurrent positions
  if ((input.accountSnapshot.openTrades ?? 0) >= 6) {
    reasons.push("MAX_OPEN_TRADES_REACHED");
  }

  // Open Risk Limit: must be < 4% of account
  // Rationale: Account blowout protection; conservative demo threshold
  if ((input.accountSnapshot.openRisk ?? 0) >= 0.04) {
    reasons.push("MAX_OPEN_RISK_REACHED");
  }

  return { approved: reasons.length === 0, reasonCodes: reasons };
}
```

**Acceptance Criteria:**
- [ ] All public functions have JSDoc with rationale
- [ ] Threshold values explained (why this number?)
- [ ] Links to requirements documentation included
- [ ] Examples provided for complex functions

---

## SUMMARY OF CRITICAL FIXES

| Issue | File | Fix | Effort | Priority |
|-------|------|-----|--------|----------|
| #1: Inference features | signal.ts | Compute actual volatility | 2h | CRITICAL |
| #2: Integration tests | integration.test.ts | Complete test suite | 3h | HIGH |
| #3: Silent model load | model-inference.ts | Add error logging | 30min | HIGH |
| #4: Portfolio transaction | portfolio.ts | Wrap in DB transaction | 2h | MEDIUM |
| #5: Config hard-coded | Multiple | Create riskLimits.ts config | 1h | MEDIUM |
| #6: Env validation | env.ts | Zod schema validation | 30min | MEDIUM |
| #7: JSDoc missing | risk-engine.ts | Document thresholds | 1h | MEDIUM |

**Total Effort:** ~10 hours for v1.0.1 release

---

**Generated:** 2026-05-20  
**Review Phase:** Issue Remediation  
**Next Step:** Implement fixes in priority order; retest; validate against v1.0 acceptance criteria
