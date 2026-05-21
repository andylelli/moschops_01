@echo off
setlocal

set "HEALTH_URL=http://localhost:3000/health"

if not "%~1"=="" set "HEALTH_URL=%~1"

if /I "%~1"=="--check" (
  echo [check-health] Ready. Default URL is http://localhost:3000/health.
  exit /b 0
)

echo [check-health] Querying %HEALTH_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $url=$env:HEALTH_URL; try { $resp=Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5; Write-Host ('[check-health] OK: ' + $url); Write-Host ('[check-health] Response: ' + ($resp | ConvertTo-Json -Compress -Depth 5)); exit 0 } catch { Write-Host ('[check-health] ERROR: ' + $_.Exception.Message); exit 1 }"
set "EXIT_CODE=%ERRORLEVEL%"

exit /b %EXIT_CODE%
