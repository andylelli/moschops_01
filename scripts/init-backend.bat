@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "ENV_FILE=%BACKEND_DIR%\.env"
set "ENV_EXAMPLE=%BACKEND_DIR%\.env.example"

if not exist "%BACKEND_DIR%\package.json" (
  echo [init-backend] ERROR: backend\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

if not exist "%ENV_EXAMPLE%" (
  echo [init-backend] ERROR: backend\.env.example not found.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [init-backend] Ready. Backend folder found at "%BACKEND_DIR%".
  exit /b 0
)

if not exist "%ENV_FILE%" (
  echo [init-backend] Creating backend\.env from .env.example...
  copy /Y "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
)

pushd "%BACKEND_DIR%" >nul

echo [init-backend] Installing backend dependencies...
call npm install
if errorlevel 1 (
  echo [init-backend] ERROR: npm install failed.
  popd >nul
  exit /b 1
)

echo [init-backend] Generating Prisma client...
call npm run prisma:generate
if errorlevel 1 (
  echo [init-backend] ERROR: prisma generate failed.
  popd >nul
  exit /b 1
)

echo [init-backend] Applying Prisma migrations...
call npm run prisma:deploy
if errorlevel 1 (
  echo [init-backend] ERROR: prisma migrate deploy failed.
  popd >nul
  exit /b 1
)

popd >nul

echo [init-backend] Backend initialization complete.
exit /b 0
