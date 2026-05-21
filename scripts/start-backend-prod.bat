@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "ENV_FILE=%BACKEND_DIR%\.env"
set "ENV_EXAMPLE=%BACKEND_DIR%\.env.example"
set "SKIP_BUILD=0"

if /I "%~1"=="--skip-build" set "SKIP_BUILD=1"

if not exist "%BACKEND_DIR%\package.json" (
  echo [backend-prod] ERROR: backend\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

if not exist "%ENV_EXAMPLE%" (
  echo [backend-prod] ERROR: backend\.env.example not found.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [backend-prod] Ready. Backend folder found at "%BACKEND_DIR%".
  exit /b 0
)

if not exist "%ENV_FILE%" (
  echo [backend-prod] backend\.env not found. Creating from .env.example...
  copy /Y "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
)

pushd "%BACKEND_DIR%" >nul

if "%SKIP_BUILD%"=="0" (
  echo [backend-prod] Building backend...
  call npm run build
  if errorlevel 1 (
    echo [backend-prod] ERROR: npm run build failed.
    popd >nul
    exit /b 1
  )
)

echo [backend-prod] Starting backend from dist...
call npm run start
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul

if not "%EXIT_CODE%"=="0" (
  echo [backend-prod] ERROR: npm run start failed.
)

exit /b %EXIT_CODE%
