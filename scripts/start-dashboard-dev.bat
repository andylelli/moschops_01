@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "DASHBOARD_DIR=%ROOT_DIR%\dashboard"

if not exist "%DASHBOARD_DIR%\package.json" (
  echo [dashboard-dev] ERROR: dashboard\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

if /I "%~1"=="--check" (
  echo [dashboard-dev] Ready. Dashboard folder found at "%DASHBOARD_DIR%".
  exit /b 0
)

echo [dashboard-dev] Starting dashboard in development mode...
pushd "%DASHBOARD_DIR%" >nul
call npm run dev
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

if not "%EXIT_CODE%"=="0" (
  echo [dashboard-dev] ERROR: npm run dev failed.
)

exit /b %EXIT_CODE%
