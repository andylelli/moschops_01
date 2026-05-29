# Backend Setup and Validation

## Prerequisites
- Node.js 20+
- Docker

## Local Database
From repository root:

```bash
docker compose up -d postgres
```

## Backend Bootstrap
From `backend/`:

```bash
cp .env.example .env
npm install
npm run prisma:generate
npm run prisma:migrate -- --name init
```

## Quality Gates
From `backend/`:

```bash
npm run build
set -a && source .env && set +a
npm run test
npm run test:db
npm run lint
```

Notes:
- `npm run test` runs fast, default checks and skips DB-dependent suites unless `RUN_DB_TESTS=true`.
- `npm run test:db` enables DB-backed integration tests and requires PostgreSQL (`docker compose up -d postgres`).
- File-based observability is written to `backend/logs/` by category (`http`, `startup`, `error`, `model`, `news`, `training`, `audit`, `security`, `db`).
- Set `LOG_DIR` in `.env` if you want a different log root; the default is `logs` under the backend working directory.
- `POST /signal` requires `marketSnapshot.volatility` as rolling volatility input.
- Startup performs ONNX model preflight; check `GET /health` telemetry for `modelLoader` state.
- `POST /portfolio/evaluate` persists decisions atomically and is replay-safe via request hash or `portfolioDecisionId`.
- `POST /training/runs` executes `../training/train_walk_forward.py`; if Python is not discoverable via PATH, set `TRAINING_PYTHON_EXECUTABLE` in backend `.env`.

## Run Service
From `backend/`:

```bash
npm run dev
```

Default health endpoint: `GET /health`
