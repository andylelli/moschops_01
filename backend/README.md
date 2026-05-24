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
npm run lint
```

Notes:
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
