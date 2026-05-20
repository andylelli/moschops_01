# Comprehensive Code Review - v1.0
## 5-Pass Quality & Accuracy Analysis

**Date:** May 20, 2026  
**Scope:** Backend (TypeScript/Fastify), MQL5 EA, Training (Python), Validation  
**Status:** Full v1.0 codebase evaluation for production readiness

---

## PASS 1: ARCHITECTURE & STRUCTURE ✅
### Assessment: Sound Design, Minor Organizational Issues

#### ✅ STRENGTHS

**1. Clean Layering (Backend)**
- Routes → Services → Domain logic separation is clean
- Risk engine abstracted as standalone service
- Model inference isolated in dedicated module
- Prisma ORM used consistently for DB access
- Good file organization: `/routes`, `/services`, `/types`, `/utils`

**2. Type Safety**
- Comprehensive Zod schemas for runtime validation
- TypeScript strict mode enforced
- Input contracts defined clearly (signalSchema, portfolioSchema)
- Response types structurally sound

**3. Modular Strategy**
- DailyBreakout strategy isolated in `/services/strategy.ts`
- Risk engine can be extended independently
- Model inference abstracted from route logic
- EA logic organized by function (CheckSafetyPreconditions, CalcPositionSize, ExecuteTrade)

#### ⚠️ CONCERNS

**1. Portfolio Route - Risk Aggregation Missing State Tracking**
- **File**: `backend/src/routes/portfolio.ts`
- **Issue**: Portfolio endpoint tracks running open risk/trades but doesn't persist decision state
- **Impact**: No audit trail of portfolio decisions; if request fails mid-evaluation, state is lost
- **Recommendation**: Either (a) persist each sub-decision atomically, or (b) wrap entire portfolio decision in transaction
- **Code snippet**:
```typescript
// Current: Sequential evaluation, no rollback mechanism
for (const plan of body.plans) {
  const result = evaluateAccountLevelRisk(...);
  if (result.approved) {
    // No DB write here - decision is only in response
    runningOpenRisk += plan.proposedRiskPct;
    runningOpenTrades += 1;
  }
}
```

**2. Signal Route - Duplicate Logic Between Routes**
- **File**: `backend/src/routes/signal.ts` and `backend/src/routes/risk.ts`
- **Issue**: Risk evaluation logic appears in both signal and dedicated risk endpoint
- **Impact**: Risk control definitions could drift; maintenance burden
- **Recommendation**: Centralize risk evaluation; both routes should call same risk-engine function

**3. MQL5 EA - Position Persistence**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5`
- **Issue**: Position state (daily reset, existing position check) stored in global variables
- **Impact**: EA restart loses tracking state; risk of multiple positions if EA crashes/restarts
- **Recommendation**: Consider persisting state to file or querying broker for confirmation

**4. Training Pipeline - Model Versioning**
- **File**: `training/train_walk_forward.py`
- **Issue**: Models exported to static path; no versioning or rollback mechanism
- **Impact**: Model updates overwrite previous versions; production model at risk
- **Recommendation**: Add timestamp/hash to model filename; maintain model registry

#### 📊 ARCHITECTURE SCORING
- **Layering**: 9/10 (excellent separation, minor state tracking gaps)
- **Modularity**: 8/10 (good isolation, some duplicate logic)
- **Extensibility**: 8/10 (easy to add new strategies/risks, versioning gaps)
- **Type Coverage**: 9/10 (strong TypeScript usage, some implicit `any` in JSON payloads)

---

## PASS 2: BUSINESS LOGIC & CORRECTNESS ✅
### Assessment: Core Logic Sound, Edge Cases Partially Addressed

#### ✅ STRENGTHS

**1. Signal Evaluation Logic (Correct)**
- **File**: `backend/src/routes/signal.ts` and `backend/src/services/strategy.ts`
- **Logic**: BUY iff (close > SMA200 AND close > Highest55); SELL iff (close < SMA200 AND close < Lowest55); else HOLD
- **Correctness**: ✅ Matches spec; no look-ahead bias
- **Test Coverage**: ✅ Deterministic signal test passing

**2. Risk Gating Rules (Correct)**
- **File**: `backend/src/services/risk-engine.ts`
- **Rules**: Max 4% open risk, 6 open trades, 0.5% per trade, spread guard
- **Correctness**: ✅ Thresholds match spec; logic is AND-based (all must pass)
- **Edge Case Handling**: ✅ Handles zero ATR, missing fields with defaults

**3. AI Thresholds (Correct)**
- **File**: `backend/src/routes/signal.ts` (lines 64-76)
- **Logic**: score ≥0.65 → FULL, 0.55-0.65 → HALF, <0.55 → SKIP
- **Correctness**: ✅ Thresholds applied correctly; sizing decision cascades properly
- **Edge Case**: ✅ Handles null score gracefully (undefined → no sizing penalty)

**4. Position Sizing Math (Correct)**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5` (lines 113-145)
- **Formula**: `lots = riskAmount / (stopDistancePips * pipValue)`
- **Validation**: ✅ Min/max/step constraints enforced; returns 0 if invalid
- **Correctness**: ✅ Risk calculation is sound; broker specs honored

#### ⚠️ CONCERNS

**1. Feature Engineering - Inference Input Mismatch**
- **File**: `backend/src/routes/signal.ts` (lines 60-66)
- **Issue**: Inference features generated on-the-fly; mismatch with training features
- **Training features** (from `train_walk_forward.py`):
  ```python
  ["trend_strength", "volatility", "spread_atr", "breakout_distance", "momentum"]
  ```
- **Runtime features** (from signal.ts):
  ```typescript
  const inferenceFeatures = [
    input.marketSnapshot.close1 - input.marketSnapshot.sma200_1,  // trend_strength
    input.marketSnapshot.atr20_1,                                   // volatility (incorrect!)
    (spread_Price) / atr20_1,                                       // spread_atr
    close1 - highestHigh55,                                         // breakout_distance
    close1 - sma100_1,                                              // momentum
  ];
  ```
- **Problem**: ATR is not "volatility"; volatility should be computed from returns. This mismatch could cause inference to behave incorrectly.
- **Impact**: AI model scores may be meaningless; strategy relying on scores operates blind
- **Recommendation**: Compute actual volatility (e.g., rolling std dev or ATR normalized); align with training definition
- **Severity**: 🔴 **MEDIUM** (model uses wrong feature; thresholds may not generalize)

**2. Portfolio Aggregation Logic - Order Dependency**
- **File**: `backend/src/routes/portfolio.ts` (lines 30-50)
- **Issue**: Approval order depends on plan order in request array
- **Example**: 
  - Plan 1: 2% risk, Plan 2: 3% risk (max 4% budget)
  - If Plan 1 first: approved; Plan 2 approved (3% margin left)
  - If Plan 2 first: approved; Plan 1 rejected (2% margin left)
- **Problem**: Non-deterministic approval across equivalent requests
- **Recommendation**: Either (a) document order-independence assumption clearly, or (b) implement approval algorithm that maximizes approved risk (knapsack-like)
- **Severity**: 🟡 **LOW-MEDIUM** (inconsistent but documented behavior acceptable if intended)

**3. Daily Reset Logic - Time Zone Handling**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5` (implied in CheckSafetyPreconditions)
- **Issue**: Daily loss tracking uses `TimeCurrent()` which is MT5 server time; unclear if conversion to UTC happens
- **Problem**: If broker is in different TZ, daily loss reset happens at wrong time
- **Recommendation**: Explicitly handle UTC conversion; document TZ assumption
- **Severity**: 🟡 **LOW** (acceptable for demo; must fix before prod)

**4. Highest/Lowest Calculation - Off-by-One Risk**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5` (lines 30-49)
- **Logic**: Loop from i=2 to i=56 (inclusive) = 55 periods
- **Correctness**: ✅ Loop bounds correct (55 bars lookback)
- **Risk**: ⚠️ If bar 0 or 1 is not yet complete, highest/lowest misses current bar
- **Recommendation**: Verify iHigh()/iLow() include current bar 0; document assumption

#### 🔍 LOGIC ERRORS TO FIX

| Issue | Severity | File | Line(s) | Fix |
|-------|----------|------|---------|-----|
| Volatility feature mismatch | MEDIUM | signal.ts | 60-66 | Compute actual rolling volatility; align with training |
| Portfolio order-dependent | LOW | portfolio.ts | 30-50 | Document or implement order-independent approval |
| TZ handling in daily loss | LOW | EA.mq5 | ~130 | Explicitly use UTC; document TZ assumption |

#### 🔢 LOGIC CORRECTNESS SCORING
- **Core strategy**: 10/10 (no bias, correct rules)
- **Risk gates**: 9/10 (correct logic, edge cases handled)
- **AI integration**: 6/10 (feature mismatch breaks inference confidence)
- **Position sizing**: 9/10 (math correct, broker specs honored)
- **Data consistency**: 7/10 (no transaction guarantees, state gaps)

---

## PASS 3: ERROR HANDLING & SAFETY ✅
### Assessment: Good Baseline, Safety Gaps in Persistence & EA

#### ✅ STRENGTHS

**1. Request Validation (Strong)**
- **File**: `backend/src/routes/signal.ts`, `portfolio.ts`
- **Method**: Zod schema validation on all inputs
- **Coverage**: ✅ Required fields validated; type checking enforced
- **Error Response**: ✅ Returns 400 with error code and message
- **Code**:
```typescript
const parsed = signalSchema.safeParse(req.body);
if (!parsed.success) {
  return reply.status(400).send({ error: { code: "INVALID_REQUEST", ... } });
}
```

**2. Risk Guard Rails (Strong)**
- **File**: `backend/src/services/risk-engine.ts`
- **Checks**: ✅ ATR validation, spread guards, trade limit enforcement
- **Fallback**: ✅ Defaults provided for missing fields (openRisk=0, etc.)
- **Effect**: Fails safe (conservative); veto on invalid data

**3. MQL5 Safety Preconditions (Good)**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5` (lines 80-117)
- **Checks**: ✅ Spread limit, margin requirement, daily loss cap
- **Response**: ✅ Trades rejected if preconditions fail; logged
- **Code**:
```mql5
bool CheckSafetyPreconditions() {
  // Spread, margin, daily loss, tradeable symbol checks
  // Returns false → trade blocked
}
```

**4. DB Persistence Isolation (Acceptable)**
- **File**: `backend/src/routes/signal.ts` (lines 104-114)
- **Approach**: ✅ Persistence wrapped in try-catch; failure doesn't block response
- **Logging**: ✅ Warnings logged on persistence failure
- **Effect**: Graceful degradation (signal still returned if DB down)

#### ⚠️ CONCERNS

**1. Model Inference - Silent Failure**
- **File**: `backend/src/services/model-inference.ts`
- **Issue**: If model file missing or corrupted, inferScore returns `null` silently
- **Problem**: Route proceeds with undefined score; no alert to operator
- **Current Code**:
```typescript
async function getSession(): Promise<ort.InferenceSession | null> {
  if (session) return session;
  
  const modelPath = path.resolve(process.cwd(), "../models/daily_breakout_model.onnx");
  if (!fs.existsSync(modelPath)) {
    return null;  // ← Silent failure; no log
  }
  session = await ort.InferenceSession.create(modelPath);
  return session;
}
```
- **Impact**: Strategy runs with degraded AI integration; no visibility
- **Recommendation**: Add explicit error logging; consider throwing instead of returning null
- **Severity**: 🟡 **MEDIUM** (breaks AI layer silently)

**2. Portfolio Endpoint - No Transaction**
- **File**: `backend/src/routes/portfolio.ts`
- **Issue**: If network fails mid-evaluation, partial approvals could be inconsistent with DB state
- **Scenario**: 5 plans evaluated, 3 approved → DB write fails → response lost → retry sends same request again
- **Problem**: No idempotency key; no rollback mechanism
- **Recommendation**: Wrap portfolio evaluation in database transaction; return decision ID for idempotency
- **Severity**: 🟡 **MEDIUM** (rare in testing, critical in prod)

**3. MQL5 EA - No Error Recovery**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5`
- **Issue**: ExecuteTrade() doesn't retry on failure; no fallback if API unreachable
- **Problem**: If backend down, EA goes silent (no trade, no alert)
- **Recommendation**: Implement retry logic; log failures; alert operator
- **Current Code**:
```mql5
bool ExecuteTrade(...) {
  if(!CheckSafetyPreconditions()) {
    Print("Trade rejected: safety preconditions failed");
    return false;  // ← No retry, no alert
  }
  // ... trade execution
}
```
- **Severity**: 🟡 **MEDIUM** (acceptable for demo; must fix before live)

**4. Signal Route - Orphaned Decisions**
- **File**: `backend/src/routes/signal.ts`
- **Issue**: If signal persisted to DB but response fails (network cut), client retries same decision
- **Risk**: Duplicate signals created; audit trail confused
- **Recommendation**: Return idempotency key (decisionId) in response; client uses it for retry deduplication
- **Severity**: 🟡 **MEDIUM** (low probability, high impact)

**5. Inference Feature Calculation - No Validation**
- **File**: `backend/src/routes/signal.ts` (lines 60-66)
- **Issue**: Feature values not validated; NaN could propagate to ONNX runtime
- **Risk**: Inference crashes silently; model undefined score returned
- **Recommendation**: Check for NaN/Infinity; log anomalies
- **Severity**: 🟡 **LOW-MEDIUM** (defensive programming)

#### 🛡️ SAFETY CONTROL MATRIX

| Control | Location | Status | Gap |
|---------|----------|--------|-----|
| Input validation | signal.ts, portfolio.ts | ✅ Strong | None |
| Risk gates | risk-engine.ts | ✅ Strong | Portfolio transaction |
| EA safety checks | EA.mq5 | ✅ Good | No retry/recovery |
| Model loading | model-inference.ts | ⚠️ Silent fail | Add error logging |
| DB persistence | signal.ts | ✅ Acceptable | No idempotency |
| Feature validation | signal.ts | ⚠️ Weak | Add NaN checks |

#### 🔐 SAFETY SCORING
- **Input validation**: 9/10 (strong Zod coverage)
- **Risk enforcement**: 8/10 (good guards, transaction gap)
- **Error handling**: 7/10 (mostly graceful, some silent failures)
- **Recovery paths**: 6/10 (no retries, no idempotency keys)
- **Observability**: 7/10 (good logging, some blind spots)

---

## PASS 4: PERFORMANCE & EFFICIENCY ⚡
### Assessment: Acceptable for Demo, Optimization Needed for Scale

#### ✅ STRENGTHS

**1. ONNX Runtime Lazy Loading**
- **File**: `backend/src/services/model-inference.ts`
- **Pattern**: Model session cached after first load; subsequent calls reuse
- **Benefit**: ✅ Avoids redundant disk I/O and model initialization
- **Efficiency**: ✅ Single session reused across all requests
- **Code**:
```typescript
let session: ort.InferenceSession | null = null;

async function getSession(): Promise<ort.InferenceSession | null> {
  if (session) return session;  // ← Cache hit
  // ... load model
}
```

**2. TimeSeriesSplit in Training**
- **File**: `training/train_walk_forward.py`
- **Method**: ✅ 5 folds, respects temporal order; no data leakage
- **Efficiency**: ✅ Single model fit per fold; parallelizable
- **Benefit**: Prevents look-ahead bias; production-grade validation

**3. Fastify Framework Choice**
- **File**: `backend/src/app.ts`
- **Benefit**: ✅ High-performance, low-overhead Node framework
- **Async**: ✅ Native async/await; non-blocking I/O
- **Middleware**: ✅ Minimal middleware stack (cors, sensible)

#### ⚠️ PERFORMANCE CONCERNS

**1. Feature Calculation - Repeated Arithmetic**
- **File**: `backend/src/routes/signal.ts` (lines 60-66)
- **Issue**: Feature array reconstructed for every signal request
- **Calculation Cost**: 5 arithmetic operations per request
- **Current Code**:
```typescript
const inferenceFeatures = [
  input.marketSnapshot.close1 - input.marketSnapshot.sma200_1,  // computed
  input.marketSnapshot.atr20_1,
  (input.marketSnapshot.spreadPrice ?? 0) / Math.max(...),       // division + max
  input.marketSnapshot.close1 - input.marketSnapshot.highestHigh55,
  input.marketSnapshot.close1 - input.marketSnapshot.sma100_1,
];
```
- **Impact**: Negligible for single signal (μs); scales poorly under load
- **Recommendation**: Pre-compute in EA; send as features field in request
- **Severity**: 🟢 **LOW** (not bottleneck, good practice)

**2. Portfolio Endpoint - O(n) Evaluation**
- **File**: `backend/src/routes/portfolio.ts` (lines 30-50)
- **Complexity**: O(n) where n = number of plans
- **Issue**: No batching; each plan evaluated sequentially
- **Scalability**: ✅ Acceptable for small batches (< 100 plans); breaks at 1000s
- **Recommendation**: Consider parallel evaluation with Promise.all(); risk aggregation remains sequential
- **Severity**: 🟡 **LOW** (not bottleneck for v1; revisit in v2)

**3. Backtest Engine - Memory Inefficiency**
- **File**: `validation/backtest_engine.py` (lines 65+)
- **Issue**: Entire price series held in memory; equity curve not pruned
- **Memory**: O(n) for n=2000 bars; acceptable for demo; breaks at millions
- **Recommendation**: Use streaming backtest for production; aggregate results incrementally
- **Severity**: 🟡 **LOW-MEDIUM** (fine for demo, must optimize for live)

**4. MQL5 EA - Highest/Lowest Loop**
- **File**: `mql5/Experts/DailyBreakoutEA.mq5` (lines 30-49)
- **Complexity**: O(55) per bar = 55 iHigh/iLow calls per OnTick
- **Frequency**: OnTick called ~10-100x/min (depends on tick rate)
- **Load**: ~550-5500 candle lookups per minute
- **Optimization**: ✅ Acceptable (lookback fixed at 55; not exponential)
- **Alternative**: Cache highest/lowest from previous bar; update incrementally
- **Severity**: 🟢 **LOW** (acceptable, could optimize for high-frequency)

#### 📊 PERFORMANCE ANALYSIS

| Component | Complexity | Status | Bottleneck | Priority |
|-----------|-----------|--------|-----------|----------|
| Signal evaluation | O(1) | ✅ | No | N/A |
| Risk checking | O(1) | ✅ | No | N/A |
| AI inference | O(1)* | ✅ | No | N/A |
| Portfolio evaluation | O(n) | ⚠️ | At 1000+ | Medium |
| EA indicators | O(55) | ✅ | No | Low |
| Backtest engine | O(n) | ⚠️ | At millions | Low |

*ONNX runtime is typically O(layers × weights); for small model ~10-100μs

#### ⏱️ PERFORMANCE SCORING
- **Runtime efficiency**: 8/10 (fast queries, lazy loading)
- **Memory usage**: 7/10 (acceptable for demo, not optimized for scale)
- **Scalability path**: 7/10 (clear optimization targets identified)
- **Load testing**: 0/10 (no load tests; blind spot)

---

## PASS 5: CODE QUALITY & STANDARDS 📝
### Assessment: Good Practices, Gaps in Documentation & Testing

#### ✅ STRENGTHS

**1. TypeScript Strict Mode**
- **File**: `backend/tsconfig.json`
- **Config**: ✅ strict: true, noImplicitAny: true, strictNullChecks: true
- **Benefit**: Type safety enforced; null/undefined caught at compile time
- **Quality**: ✅ No implicit any; discriminated unions used for safety

**2. Naming Conventions**
- **Backend**: ✅ camelCase consistently applied (evaluateSignalLevelRisk, portfolioRoutes)
- **MQL5**: ✅ PascalCase for functions (IsNewCompletedBar, CheckSafetyPreconditions)
- **Python**: ✅ snake_case standard (walk_forward_metrics, make_synthetic_bars)
- **Clarity**: ✅ Names are self-documenting; function purposes clear

**3. Function Decomposition**
- **Pattern**: Well-separated concerns (risk, strategy, inference isolated)
- **Example**: MQL5 EA broken into functions (CalcPositionSize, ExecuteTrade, CheckSafetyPreconditions)
- **Testability**: ✅ Each function single responsibility; mockable

**4. Zod Schema Definition**
- **File**: `backend/src/routes/signal.ts`, `portfolio.ts`
- **Pattern**: ✅ Schemas co-located with routes; clear contract definition
- **Validation**: ✅ Runtime type safety; catches invalid payloads early
- **Usability**: ✅ Inferred TypeScript types from schemas

#### ⚠️ QUALITY GAPS

**1. Missing JSDoc/Comments in Key Functions**
- **File**: `backend/src/services/risk-engine.ts` (evaluateSignalLevelRisk, evaluateAccountLevelRisk)
- **Issue**: No parameter descriptions; threshold values hard-coded with no context
- **Example Missing Docs**:
```typescript
export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
  const reasons: string[] = [];
  const atr = input.marketSnapshot.atr20_1;
  const spread = input.marketSnapshot.spreadPrice ?? 0;

  if (spread > 0 && atr > 0 && spread / atr > 0.2) {  // ← Why 0.2?
    reasons.push("SPREAD_TOO_WIDE");
  }
  // ... no comment explaining threshold origin
}
```
- **Recommendation**: Add JSDoc with threshold rationale; link to requirements
- **Example Fix**:
```typescript
/**
 * Evaluate signal-level risk controls.
 * 
 * @param input Signal request with market/account snapshots
 * @returns Risk decision with approval status and reason codes
 * 
 * Constraints checked:
 * - ATR must be positive (indicates tradeable market)
 * - Spread/ATR ratio ≤ 0.2 (prevents trades in wide-spread conditions)
 * - Open trades < 6 (portfolio concentration limit)
 * - Open risk < 4% (account protection limit, per LLD v1)
 * 
 * See: docs/02-architecture/lld_v1.md § Risk Engine Controls
 */
export function evaluateSignalLevelRisk(input: SignalRequest): RiskDecision {
```
- **Severity**: 🟡 **MEDIUM** (maintainability risk)

**2. No Error Type Definitions**
- **File**: `backend/src/routes/*.ts`
- **Issue**: Error responses use ad-hoc objects; no typed error schema
- **Current**:
```typescript
return reply.status(400).send({ error: { code: "INVALID_REQUEST", message: parsed.error.message } });
```
- **Problem**: Caller doesn't know error shape; no IDE autocomplete
- **Recommendation**: Define error type; use Zod schema
```typescript
const ErrorResponse = z.object({
  error: z.object({
    code: z.enum(["INVALID_REQUEST", "RISK_VETOED", "INTERNAL_ERROR"]),
    message: z.string(),
    details: z.record(z.string(), z.any()).optional(),
  }),
});
```
- **Severity**: 🟡 **LOW-MEDIUM** (API contract incomplete)

**3. Test Coverage Gaps**
- **File**: Test files (app.test.ts, integration.test.ts)
- **Current**: 3/9 tests passing; 6 skipped/failing
- **Gap**: No tests for:
  - Risk engine threshold edge cases (spread/atr = 0.2 boundary)
  - Feature calculation (NaN handling)
  - Model loading failure scenario
  - Portfolio order-dependency
  - Idempotent signal writes
- **Coverage**: ~30% of critical paths; needs 80%+
- **Recommendation**: Fix integration tests; add edge case tests
- **Severity**: 🔴 **HIGH** (untested code = unvalidated code)

**4. No Logging of Thresholds & Decisions**
- **File**: `backend/src/services/risk-engine.ts`
- **Issue**: Why thresholds were chosen not logged or traced
- **Problem**: Operator can't understand risk decisions; auditing hard
- **Example**: "SPREAD_TOO_WIDE" - but what was spread/atr ratio?
- **Recommendation**: Include threshold values in reason codes or structured logging
```typescript
// Instead of: "SPREAD_TOO_WIDE"
// Log: { reasonCode: "SPREAD_TOO_WIDE", context: { spreadAtrRatio: 0.25, threshold: 0.2 } }
```
- **Severity**: 🟡 **MEDIUM** (operational/audit concern)

**5. Python Module Organization**
- **File**: `training/train_walk_forward.py`
- **Issue**: All code in single file; no module structure
- **Complexity**: 250+ lines; mixing data generation, model training, ONNX export
- **Recommendation**: Split into modules:
  - `training/dataset.py` (data generation, features)
  - `training/models.py` (model builders)
  - `training/metrics.py` (walk-forward evaluation)
  - `training/export.py` (ONNX export)
- **Severity**: 🟡 **LOW** (fine for demo; must refactor for maintenance)

**6. No Configuration Management**
- **File**: Threshold values hard-coded across codebase
- **Examples**:
  - Max open risk: 4% (signal.ts, risk-engine.ts, portfolio.ts) ← repeated 3x
  - Max open trades: 6 (repeated)
  - Spread/ATR ratio: 0.2 (repeated)
  - AI thresholds: 0.65, 0.55 (repeated)
- **Problem**: Changing thresholds requires code edits in multiple places
- **Recommendation**: Create config module:
```typescript
// src/config/riskLimits.ts
export const RISK_LIMITS = {
  maxOpenRiskPct: 0.04,
  maxOpenTrades: 6,
  maxSpreadAtrRatio: 0.2,
  aiScoreThresholds: { full: 0.65, half: 0.55 },
} as const;
```
- **Severity**: 🟡 **MEDIUM** (maintainability & compliance)

**7. No Environment Configuration Schema**
- **File**: `backend/src/utils/env.ts`
- **Issue**: Environment variables not validated at startup
- **Risk**: Missing DATABASE_URL silently becomes undefined
- **Recommendation**: Use Zod to validate all required env vars on app start
```typescript
const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().default(3000),
  NODE_ENV: z.enum(["development", "production"]),
});

const env = EnvSchema.parse(process.env);
```
- **Severity**: 🟡 **MEDIUM** (deployment risk)

**8. Missing CHANGELOG**
- **Issue**: No record of v1.0 features, changes, known issues
- **Impact**: New team members can't understand history; hard to track breaking changes
- **Recommendation**: Create CHANGELOG.md with v1.0 release notes
- **Severity**: 🟡 **LOW** (documentation, not code)

#### 📋 CODE QUALITY CHECKLIST

| Item | Status | Gap |
|------|--------|-----|
| TypeScript strict mode | ✅ | None |
| Naming conventions | ✅ | None |
| Function decomposition | ✅ | Module organization (Python) |
| Type safety | ✅ | Error type schemas |
| Test coverage | ⚠️ | 30% → need 80%+ |
| Documentation | ⚠️ | Missing JSDoc in services; threshold rationale undocumented |
| Error handling | ⚠️ | Ad-hoc error responses |
| Configuration | ⚠️ | Hard-coded thresholds; env vars not validated |
| Logging | ⚠️ | Decision context not included |

#### 📚 DOCUMENTATION SCORING
- **Code comments**: 6/10 (sparse; missing threshold rationale)
- **API documentation**: 6/10 (Zod schemas good; error types missing)
- **Operational docs**: 7/10 (README present; threshold docs missing)
- **Test coverage**: 4/10 (core paths only; edge cases untested)
- **Configuration**: 5/10 (env.ts exists; no startup validation)

---

## SUMMARY SCORECARD

| Dimension | Score | Status | Priority Fix |
|-----------|-------|--------|--------------|
| **Architecture** | 8.5/10 | ✅ Sound | Portfolio transaction safety |
| **Business Logic** | 7.5/10 | ⚠️ Mostly correct | Fix inference features; test edge cases |
| **Error Handling** | 7/10 | ⚠️ Acceptable | Add retry logic; model load logging |
| **Performance** | 7.5/10 | ✅ Acceptable | No immediate bottlenecks |
| **Code Quality** | 6.5/10 | ⚠️ Good baseline | Documentation; test coverage; config |
| **Overall v1.0** | **7.4/10** | ✅ **DEMO-READY** | See action items below |

---

## CRITICAL FINDINGS

### 🔴 MUST FIX BEFORE PRODUCTION
1. **Inference feature mismatch** (volatility != ATR) - Logic broken
2. **Missing integration tests** - 6/9 failing; untested code path
3. **No idempotency keys** - Risk of duplicate signals
4. **Silent model load failures** - No visibility into AI layer

### 🟡 SHOULD FIX BEFORE NEXT RELEASE (v1.1)
1. Portfolio transaction safety (wrap in DB transaction)
2. MQL5 EA retry logic (handle backend unavailability)
3. Configuration externaliza (end hard-coded thresholds)
4. Comprehensive JSDoc (threshold rationale, contract docs)
5. Env var validation (Zod schema at startup)

### 🟢 NICE TO HAVE (v1.2+)
1. Load testing (establish performance baselines)
2. Python module refactoring (split train_walk_forward.py)
3. Error type definitions (typed error responses)
4. Logging context enrichment (decision context in logs)
5. Dashboard API wiring (connect UI to live data)

---

## ACTION PLAN FOR v1.0 STABILIZATION

### **Immediate (Before Demo)**
- [ ] Fix signal feature calculation: Compute actual volatility; validate against training features
- [ ] Update integration tests: Ensure all 9 tests pass
- [ ] Add model load logging: "ERROR: Model not found at {path}" instead of silent null

### **Before v1.0 Production Release (v1.0.1)**
- [ ] Wrap portfolio endpoint in database transaction
- [ ] Add idempotency key to signal response (use decisionId)
- [ ] Implement EA retry logic (3x retry with exponential backoff)
- [ ] Create RiskLimits config module (centralize thresholds)
- [ ] Add JSDoc to risk-engine.ts with threshold rationale

### **v1.1 Release**
- [ ] Fix all integration tests (6 failing)
- [ ] Validate env vars at app startup (Zod schema)
- [ ] Add comprehensive error type definitions
- [ ] Implement decision logging with context (threshold values, feature values)
- [ ] Refactor training module (split into submodules)

---

## NOTES FOR TEAM

1. **v1.0 is demo-ready** with minor caveats:
   - Core logic correct (strategy, risk gates, position sizing)
   - Type safety strong (TypeScript strict)
   - Safety guards in place (spread checks, margin requirements)
   - Data persistence working (PostgreSQL, Prisma)

2. **Key gaps for production** (not demo-blockers):
   - Error handling needs hardening (retries, idempotency)
   - Tests need expansion (currently 30% coverage)
   - Documentation needs depth (threshold rationale missing)
   - Observability needs investment (decision logging sparse)

3. **Inference layer caution**:
   - Feature calculation mismatch with training means AI scores may be wrong
   - Recommend testing model predictions against training data first
   - Consider disabling AI sizing (set all scores to undefined) until fixed

4. **No blocker for demo**, but fix #1 (inference features) before relying on AI for production decisions.

---

**Generated:** 2026-05-20  
**Review Lead:** Code Quality Audit Agent  
**Next Review:** After v1.0 stabilization fixes applied
