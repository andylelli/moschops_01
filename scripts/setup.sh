#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi

  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi

  echo ""
}

echo "[setup] checking prerequisites"
require_cmd docker
require_cmd node
require_cmd npm
require_cmd python3
require_cmd pip

COMPOSE_BIN="$(compose_cmd)"
if [[ -z "$COMPOSE_BIN" ]]; then
  echo "Missing required command: docker-compose or docker compose"
  exit 1
fi

echo "[setup] ensuring backend environment file exists"
if [[ ! -f "$ROOT_DIR/backend/.env" ]]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
  echo "[setup] created backend/.env from template"
fi

echo "[setup] starting postgres with docker-compose"
cd "$ROOT_DIR"
$COMPOSE_BIN up -d postgres

echo "[setup] installing backend dependencies"
cd "$ROOT_DIR/backend"
npm install

echo "[setup] applying prisma migrations"
set -a
source .env
set +a
npx prisma migrate deploy

echo "[setup] installing dashboard dependencies"
cd "$ROOT_DIR/dashboard"
npm install

echo "[setup] installing training dependencies"
cd "$ROOT_DIR/training"
pip install -r requirements.txt

echo "[setup] regenerating ONNX model artifact"
python3 train_walk_forward.py --model logreg --output ../models

echo "[setup] done"
echo "[setup] next: run backend with 'cd backend && npm run dev'"
echo "[setup] next: run dashboard with 'cd dashboard && npm run dev'"
