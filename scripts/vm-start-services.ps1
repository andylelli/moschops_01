# vm-start-services.ps1
# Starts the Fastify backend and MT5 terminal on every workflow run.
# Both processes run on the same VM so the EA can reach the backend at 127.0.0.1:3000.
#
# Parameters (positional, passed via --parameters in the workflow):
#   $args[0]  MT5_LOGIN     MT5 broker account number
#   $args[1]  MT5_PASSWORD  MT5 broker account password
#   $args[2]  MT5_SERVER    MT5 broker server name  (e.g. MetaQuotes-Demo)

param(
    [string]$MT5_LOGIN,
    [string]$MT5_PASSWORD,
    [string]$MT5_SERVER
)

$ErrorActionPreference = "Stop"

$AppDir      = "C:\moschops"
$LogDir      = "$AppDir\logs"
$MT5Exe      = "C:\Program Files\MetaTrader 5\terminal64.exe"
$MetaEditor  = "C:\Program Files\MetaTrader 5\metaeditor64.exe"
$ExpertSrc   = "$AppDir\mql5\Experts\DailyBreakoutEA.mq5"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Add-ToPath([string]$Dir) {
    if ($env:Path -notlike "*$Dir*") {
        $env:Path = "$Dir;$env:Path"
    }
}

Add-ToPath "C:\ProgramData\chocolatey\bin"
Add-ToPath "C:\Program Files\nodejs"

# ── Restart backend via NSSM ──────────────────────────────────────────────────

Write-Output "=== Starting backend service ==="

$svc = Get-Service -Name "moschops-backend" -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "NSSM service 'moschops-backend' not found. Ensure provisioning completed successfully."
    exit 1
}

& nssm.exe restart moschops-backend
Write-Output "Backend service restarted."

# Wait for backend to be ready (up to 60s)
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Warning "Backend did not respond on /health within 60s. Check $LogDir\backend_error.log."
} else {
    Write-Output "Backend is healthy at http://127.0.0.1:3000"
}

# ── Deploy and compile EA ─────────────────────────────────────────────────────

Write-Output ""
Write-Output "=== Deploying and compiling EA ==="

if (-not (Test-Path $ExpertSrc)) {
    Write-Error "EA source not found: $ExpertSrc"
    exit 1
}

$mt5DataRoot = "$env:APPDATA\MetaQuotes\Terminal"
if (-not (Test-Path $mt5DataRoot)) {
    Write-Warning "MT5 data directory not found at $mt5DataRoot. MT5 may not have run yet — skipping EA deploy."
} else {
    Get-ChildItem $mt5DataRoot -Directory | ForEach-Object {
        $expertDir = "$($_.FullName)\MQL5\Experts"
        New-Item -ItemType Directory -Force -Path $expertDir | Out-Null

        # Copy source file
        Copy-Item -Path $ExpertSrc -Destination $expertDir -Force
        Write-Output "  EA source copied to $expertDir"

        # Compile to .ex5 using MetaEditor command-line
        if (Test-Path $MetaEditor) {
            $mq5Path = "$expertDir\DailyBreakoutEA.mq5"
            Write-Output "  Compiling $mq5Path ..."
            Start-Process -FilePath $MetaEditor `
                -ArgumentList "/compile:`"$mq5Path`" /log" `
                -Wait -NoNewWindow
            if (Test-Path "$expertDir\DailyBreakoutEA.ex5") {
                Write-Output "  Compiled successfully: DailyBreakoutEA.ex5"
            } else {
                Write-Warning "  Compilation may have failed — .ex5 not found. Check MetaEditor log."
            }
        } else {
            Write-Warning "  MetaEditor not found at $MetaEditor — EA will be compiled on next MT5 start."
        }
    }
}

# ── Register MT5 auto-start and launch ───────────────────────────────────────

Write-Output ""
Write-Output "=== Starting MT5 ==="

if (-not (Test-Path $MT5Exe)) {
    Write-Error "MT5 executable not found at $MT5Exe"
    exit 1
}

# Register MT5 as a Task Scheduler task that runs at user logon (survives reboots)
$taskName = "MT5 AutoStart"
$action   = New-ScheduledTaskAction `
    -Execute  $MT5Exe `
    -Argument "/Login:$MT5_LOGIN /Password:$MT5_PASSWORD /Server:$MT5_SERVER"
$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask `
    -TaskName $taskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force    | Out-Null
Write-Output "  Task Scheduler entry '$taskName' registered (auto-start on logon)."

# Launch MT5 immediately (GUI app — don't wait)
Start-Process `
    -FilePath  $MT5Exe `
    -ArgumentList "/Login:$MT5_LOGIN /Password:$MT5_PASSWORD /Server:$MT5_SERVER" `
    -WindowStyle Minimized

Write-Output "  MT5 launched."
Write-Output ""
Write-Output "Services running:"
Write-Output "  Backend : http://127.0.0.1:3000  (Windows service: moschops-backend)"
Write-Output "  MT5     : running, auto-start on logon registered"
Write-Output "  Logs    : $LogDir"
