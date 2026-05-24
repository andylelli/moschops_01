# moschops

Moschops is an AI-assisted trading platform with a deterministic execution core, risk-first backend APIs, audit logging, ONNX inference, and an operator dashboard.

## What Is In This Repository

- MQL5 expert advisor and includes for strategy execution.
- Fastify + TypeScript backend with Prisma/PostgreSQL persistence.
- Vue 3 dashboard for system health, risk, portfolio, and signal visibility.
- Python training and validation tooling for model lifecycle.
- Governance, architecture, API, and operations documentation.

## Architecture Summary

1. EA emits market and trade context to backend API endpoints.
2. Backend validates strategy contract, applies risk controls, and scores model input.
3. Decisions and audit data are persisted for traceability and replay-safe behavior.
4. Dashboard reads health, metrics, portfolio, and trade state for operations.

Core reliability behaviors in current implementation:

- Strict signal schema includes required `marketSnapshot.volatility`.
- Startup model preflight with degraded/available model loader telemetry on `GET /health`.
- Idempotent signal replay and portfolio evaluation replay semantics.
- Atomic portfolio persistence for parent/child decision records.

## Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- Docker with Compose
- Python 3.10+ and pip (for training pipeline)

### Option A: Full Setup (Linux/macOS/WSL)

From repository root:

```bash
./scripts/setup.sh
```

This script starts PostgreSQL, installs backend/dashboard dependencies, applies migrations, installs Python requirements, and regenerates ONNX artifacts.

### Option B: Windows Node Dependency Install

From repository root in Command Prompt or PowerShell:

```bat
scripts\install-node-modules.bat
```

This installs Node dependencies for both `backend` and `dashboard`.

### Option C: Windows Backend Start Scripts

From repository root in Command Prompt or PowerShell:

```bat
scripts\start-backend-dev.bat
```

This starts the backend in development mode (`npm run dev`).

```bat
scripts\start-backend-prod.bat
```

This builds and starts the backend from `dist` (`npm run build` then `npm run start`).

### Option D: Windows Local Stack Scripts

From repository root in Command Prompt or PowerShell:

```bat
scripts\start-db.bat
scripts\init-backend.bat
scripts\start-dashboard-dev.bat
scripts\start-dev-stack.bat
scripts\check-local-health.bat
scripts\stop-db.bat
scripts\deploy-ea-to-mt5.bat "C:\\Users\\USER\\AppData\\Roaming\\MetaQuotes\\Terminal\\INSTANCE_ID"
```

What each script does:

- `start-db.bat`: starts PostgreSQL with Docker Compose.
- `init-backend.bat`: creates `backend/.env` if missing, installs deps, generates Prisma client, and runs migrations.
- `start-dashboard-dev.bat`: starts the dashboard development server.
- `start-dev-stack.bat`: starts DB and launches backend/dashboard dev servers in separate terminal windows.
- `check-local-health.bat`: checks backend health endpoint (`http://localhost:3000/health` by default).
- `stop-db.bat`: stops PostgreSQL service.
- `deploy-ea-to-mt5.bat`: copies `mql5/Experts/DailyBreakoutEA.mq5` into the selected MT5 data directory under `MQL5/Experts`.

## Run Locally

### 1) Start PostgreSQL

```bash
docker compose up -d postgres
```

### 2) Configure Backend Environment

```bash
cp backend/.env.example backend/.env
```

### 3) Run Backend

```bash
cd backend
npm run dev
```

Default backend address: `http://localhost:3000`

### 4) Run Dashboard

```bash
cd dashboard
npm run dev
```

Default dashboard address: `http://localhost:5173`

## Useful Commands

### Backend

```bash
cd backend
npm run build
npm run test
npm run lint
```

### Dashboard

```bash
cd dashboard
npm run build
```

### Prisma

```bash
cd backend
npx prisma migrate deploy
npx prisma migrate status
```

## API Surface

Primary endpoints exposed by the backend:

- `POST /signal`
- `POST /risk-check`
- `POST /portfolio/evaluate`
- `POST /log-signal`
- `POST /log-rejected-signal`
- `POST /log-trade`
- `POST /trades/open`
- `GET /trades/open`
- `GET /model-version`
- `GET /performance`
- `GET /health`

For request/response contracts and error rules, see the API spec linked below.

## Project Layout

- `backend`: Fastify API, risk engine, model inference, Prisma schema/migrations, tests.
- `dashboard`: Vue operator UI.
- `training`: model training and ONNX export pipeline.
- `validation`: baseline/backtest scripts and validation notes.
- `mql5`: EA and include files for MT5 integration.
- `models`: generated model artifacts and training report.
- `docs`: architecture/specs/governance/operations/UI documentation.

## Documentation Index

- Setup: [SETUP.md](SETUP.md)
- Roadmap: [docs/01-roadmap/coding_plan.md](docs/01-roadmap/coding_plan.md)
- LLD v1: [docs/02-architecture/lld_v1.md](docs/02-architecture/lld_v1.md)
- LLD v2: [docs/02-architecture/lld_v2.md](docs/02-architecture/lld_v2.md)
- API contracts: [docs/03-specifications/api_contract_specification.md](docs/03-specifications/api_contract_specification.md)
- Data lineage: [docs/03-specifications/data_dictionary_and_lineage.md](docs/03-specifications/data_dictionary_and_lineage.md)
- Model governance: [docs/03-specifications/model_governance_standard.md](docs/03-specifications/model_governance_standard.md)
- Operations and security: [docs/04-operations/security_and_access_control.md](docs/04-operations/security_and_access_control.md)
- UI design: [docs/05-ui/ui_design.md](docs/05-ui/ui_design.md)
- Runbook tracker: [docs/00-governance/implementation_runbook.md](docs/00-governance/implementation_runbook.md)

## Notes

- Keep dependency folders and build output out of commits (`node_modules`, `dist`).
- Use explicit path staging for commits when working in a dirty tree.
- For MT5 deployment workflow and real-data training expectations, follow [SETUP.md](SETUP.md).