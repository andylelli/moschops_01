@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
set "COMPOSE_FILE=%ROOT_DIR%\docker-compose.yml"
set "POSTGRES_HOST_PORT=%POSTGRES_HOST_PORT%"

if not defined POSTGRES_HOST_PORT (
  for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$preferred = 5432..5445; foreach ($port in $preferred) { if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) { $port; break } }"') do (
    set "POSTGRES_HOST_PORT=%%P"
  )
) else (
  for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-NetTCPConnection -LocalPort $env:POSTGRES_HOST_PORT -State Listen -ErrorAction SilentlyContinue)) { $env:POSTGRES_HOST_PORT }"') do (
    set "POSTGRES_HOST_PORT=%%P"
  )
)

if not exist "%COMPOSE_FILE%" (
  echo [start-db] ERROR: docker-compose.yml not found. Run this script from the repository scripts folder.
  exit /b 1
)

where docker >nul 2>&1
if errorlevel 1 (
  echo [start-db] ERROR: docker CLI not found in PATH.
  echo [start-db] Install Docker Desktop and ensure the docker command is available.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [start-db] ERROR: Docker engine is not running.
  echo [start-db] Start Docker Desktop and wait until the engine is running, then retry.
  exit /b 1
)

if not defined POSTGRES_HOST_PORT (
  echo [start-db] ERROR: Unable to find a free host port for PostgreSQL.
  exit /b 1
)

if /I not "%POSTGRES_HOST_PORT%"=="5432" (
  echo [start-db] WARNING: Port 5432 is already in use. Using %POSTGRES_HOST_PORT% for PostgreSQL instead.
)

if /I "%~1"=="--check" (
  echo [start-db] Ready. Compose file found at "%COMPOSE_FILE%" and host port %POSTGRES_HOST_PORT% is available.
  exit /b 0
)

echo [start-db] Starting postgres service...
pushd "%ROOT_DIR%" >nul
set "POSTGRES_HOST_PORT=%POSTGRES_HOST_PORT%"
docker compose up -d postgres
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

if not "%EXIT_CODE%"=="0" (
  echo [start-db] ERROR: docker compose up failed.
)

endlocal & set "POSTGRES_HOST_PORT=%POSTGRES_HOST_PORT%" & exit /b %EXIT_CODE%
