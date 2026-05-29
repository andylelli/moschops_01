@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "SCRIPTS_DIR=%ROOT_DIR%\scripts"

if not exist "%SCRIPTS_DIR%\start-db.bat" (
  echo [start-dev-stack] ERROR: scripts\start-db.bat not found.
  exit /b 1
)

if not exist "%SCRIPTS_DIR%\start-backend-dev.bat" (
  echo [start-dev-stack] ERROR: scripts\start-backend-dev.bat not found.
  exit /b 1
)

if not exist "%SCRIPTS_DIR%\start-dashboard-dev.bat" (
  echo [start-dev-stack] ERROR: scripts\start-dashboard-dev.bat not found.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [start-dev-stack] Ready. Required scripts are available.
  exit /b 0
)

call "%SCRIPTS_DIR%\start-db.bat"
if errorlevel 1 (
  echo [start-dev-stack] ERROR: Database startup failed.
  echo [start-dev-stack] Resolve docker issues first, then rerun this script.
  exit /b 1
)

if not defined POSTGRES_HOST_PORT set "POSTGRES_HOST_PORT=5432"
set "DATABASE_URL=postgresql://postgres:postgres@localhost:%POSTGRES_HOST_PORT%/moschops"

echo [start-dev-stack] Using PostgreSQL host port %POSTGRES_HOST_PORT%.

echo [start-dev-stack] Launching backend window...
start "moschops-backend-dev" cmd /k ""%SCRIPTS_DIR%\start-backend-dev.bat""

echo [start-dev-stack] Launching dashboard window...
start "moschops-dashboard-dev" cmd /k ""%SCRIPTS_DIR%\start-dashboard-dev.bat""

echo [start-dev-stack] Started postgres, backend, and dashboard.
exit /b 0
