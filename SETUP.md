# Setup and Installation Guide

This guide covers local platform setup, MT5 integration, and real historical data collection for training.

## 1. Prerequisites

- Operating system for backend and training: Ubuntu 22.04 or newer, or WSL2 Ubuntu.
- Operating system for MT5 terminal: Windows 10 or newer.
- Node.js 18 or newer.
- npm 9 or newer.
- Docker and Docker Compose v2.
- Python 3.10 or newer and pip.
- MetaTrader 5 terminal installed on Windows host.

## 2. Clone Repository

Use the repository URL and open the workspace root.

## 3. One-command Local Setup

Run the setup script from repository root:

./scripts/setup.sh

For Windows-only Node dependency install (backend + dashboard), run:

scripts\install-node-modules.bat

The script does the following:

- Starts PostgreSQL with Docker Compose.
- Installs backend and dashboard dependencies.
- Applies Prisma migrations.
- Installs Python training dependencies.
- Regenerates ONNX model artifact.

## 4. Environment Configuration

Copy backend environment file and verify values:

cp backend/.env.example backend/.env

Required values:

- DATABASE_URL
- NODE_ENV
- LOG_LEVEL
- PORT

Optional values for wizard-triggered training execution:

- TRAINING_PYTHON_EXECUTABLE (set when Python is not resolvable via `py` or `python` in PATH)
- TRAINING_TIMEOUT_SECONDS (default 600)

## 5. Run Services

Backend:

cd backend
npm run dev

Dashboard:

cd dashboard
npm run dev

## 6. Run Backend Tests

cd backend
set -a && source .env && set +a
npm run test

## 7. MT5 Setup and Backend Wiring

1. Install and open MetaTrader 5 on Windows host.
2. Log in to a demo account.
3. Deploy EA source into your MT5 terminal data folder:

```bat
scripts\deploy-ea-to-mt5.bat "C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\INSTANCE_ID"
```

4. Compile and attach EA from MQL5/Experts/DailyBreakoutEA.mq5 in MetaEditor.
5. In MT5 options, enable Algo Trading.
6. In MT5 options, enable WebRequest and allow backend base URL.
7. Verify EA payload includes required marketSnapshot.volatility value.
8. Run controlled dry test and confirm backend receives signal and risk-check requests.

Credentials note:

- Keep broker login/password/server in MT5 terminal only. Do not store MT5 account credentials in repository files.

## 8. Real Historical Data for Training

Current training script can export ONNX and run walk-forward checks. Production-quality training requires real historical data.

Minimum collection targets:

- 3 to 5 years of D1 data per traded symbol.
- Multiple regimes: trend, range, and high-volatility periods.
- Feature parity with runtime inference payload.

Required data fields per sample:

- decisionId, symbol, timeframe, barCloseTimeUtc.
- trend_strength, volatility, spread_atr, breakout_distance, momentum.
- spread, slippage, strategyVersion, modelVersion.
- label outcome: +2R before -1R within horizon.

Recommended acquisition path:

1. Export MT5 bars and relevant execution context from demo account history.
2. Persist signal, feature, trade, and outcome data to PostgreSQL.
3. Build dataset extraction and label jobs in training pipeline.
4. Retrain model with real dataset and run out-of-sample validation.
5. Promote model only after governance checks pass.

## 9. Model Export and Runtime Compatibility

- ONNX export uses tensor probability output to match Node runtime.
- Model preflight runs at backend startup.
- Health endpoint reports model loader state.

## 10. Troubleshooting

- Docker health: docker ps
- DB migration status: cd backend && npx prisma migrate status
- Backend compile check: cd backend && npm run build
- Backend tests: cd backend && set -a && source .env && set +a && npm run test

## 11. References

- docs/03-specifications/api_contract_specification.md
- docs/03-specifications/model_governance_standard.md
- docs/03-specifications/data_dictionary_and_lineage.md
- docs/04-operations/environment_and_deployment_topology.md
