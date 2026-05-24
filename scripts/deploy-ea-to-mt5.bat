@echo off
setlocal

set "ROOT_DIR=%~dp0.."
set "EA_SOURCE=%ROOT_DIR%\mql5\Experts\DailyBreakoutEA.mq5"

if /I "%~1"=="--check" (
  if not exist "%EA_SOURCE%" (
    echo [deploy-ea] ERROR: EA source not found at "%EA_SOURCE%".
    exit /b 1
  )

  echo [deploy-ea] Ready. Usage: scripts\deploy-ea-to-mt5.bat "MT5_DATA_PATH"
  exit /b 0
)

if "%~1"=="" (
  echo [deploy-ea] ERROR: Missing MT5 data path.
  echo [deploy-ea] Usage: scripts\deploy-ea-to-mt5.bat "C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\INSTANCE_ID"
  exit /b 1
)

if not exist "%EA_SOURCE%" (
  echo [deploy-ea] ERROR: EA source not found at "%EA_SOURCE%".
  exit /b 1
)

set "MT5_DATA_PATH=%~1"

if not exist "%MT5_DATA_PATH%" (
  echo [deploy-ea] ERROR: MT5 data path does not exist: "%MT5_DATA_PATH%".
  exit /b 1
)

set "TARGET_DIR=%MT5_DATA_PATH%\MQL5\Experts"
set "TARGET_FILE=%TARGET_DIR%\DailyBreakoutEA.mq5"

if not exist "%TARGET_DIR%" (
  mkdir "%TARGET_DIR%"
  if errorlevel 1 (
    echo [deploy-ea] ERROR: Unable to create target directory "%TARGET_DIR%".
    exit /b 1
  )
)

copy /Y "%EA_SOURCE%" "%TARGET_FILE%" >nul
if errorlevel 1 (
  echo [deploy-ea] ERROR: Failed to copy EA to "%TARGET_FILE%".
  exit /b 1
)

echo [deploy-ea] EA deployed to "%TARGET_FILE%".
echo [deploy-ea] Next: Open MT5 MetaEditor, compile DailyBreakoutEA.mq5, then attach to chart.
exit /b 0
