@echo off
setlocal

set "ROOT_DIR=%~dp0.."

if not exist "%ROOT_DIR%\backend\package.json" (
  echo [install] ERROR: backend\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

if not exist "%ROOT_DIR%\dashboard\package.json" (
  echo [install] ERROR: dashboard\package.json not found. Run this script from the repository scripts folder.
  exit /b 1
)

call :install backend
if errorlevel 1 exit /b 1

call :install dashboard
if errorlevel 1 exit /b 1

echo [install] Node modules installation complete.
exit /b 0

:install
set "TARGET=%~1"
echo [install] Installing %TARGET% dependencies...
pushd "%ROOT_DIR%\%TARGET%" >nul
call npm install
if errorlevel 1 (
  echo [install] ERROR: npm install failed in %TARGET%.
  popd >nul
  exit /b 1
)
popd >nul
exit /b 0