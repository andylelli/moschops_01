@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "COMPOSE_FILE=%ROOT_DIR%\docker-compose.yml"

if not exist "%COMPOSE_FILE%" (
  echo [start-db] ERROR: docker-compose.yml not found. Run this script from the repository scripts folder.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [start-db] Ready. Compose file found at "%COMPOSE_FILE%".
  exit /b 0
)

echo [start-db] Starting postgres service...
pushd "%ROOT_DIR%" >nul
docker compose up -d postgres
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

if not "%EXIT_CODE%"=="0" (
  echo [start-db] ERROR: docker compose up failed.
)

exit /b %EXIT_CODE%
