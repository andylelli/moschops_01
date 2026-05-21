@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "ENV_FILE=%BACKEND_DIR%\.env"
set "ENV_EXAMPLE=%BACKEND_DIR%\.env.example"

if not exist "%BACKEND_DIR%\package.json" (
  echo [backend-dev] ERROR: backend\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

if not exist "%ENV_EXAMPLE%" (
  echo [backend-dev] ERROR: backend\.env.example not found.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [backend-dev] Ready. Backend folder found at "%BACKEND_DIR%".
  exit /b 0
)

if not exist "%ENV_FILE%" (
  echo [backend-dev] backend\.env not found. Creating from .env.example...
  copy /Y "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
)

echo [backend-dev] Starting backend in development mode...
pushd "%BACKEND_DIR%" >nul
call npm run dev
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

if not "%EXIT_CODE%"=="0" (
  echo [backend-dev] ERROR: npm run dev failed.
)

exit /b %EXIT_CODE%
