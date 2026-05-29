# vm-provision.ps1
# Runs on every workflow start via az vm run-command invoke.
# On first run: installs all software, clones repo, builds backend, migrates DB, installs MT5.
# On subsequent runs: pulls latest code and rebuilds.
#
# Parameters (positional, passed via --parameters in the workflow):
#   $GH_PAT        GitHub Personal Access Token (repo read access)
#   $REPO          GitHub repo slug, e.g. andylelli/moschops_01
#   $DATABASE_URL  PostgreSQL connection string (postgresql://postgres:<pass>@localhost:5432/moschops)
#   $FMP_API_KEY   Financial Modeling Prep API key

param(
    [string]$GH_PAT,
    [string]$REPO,
    [string]$DATABASE_URL,
    [string]$FMP_API_KEY
)

$ErrorActionPreference = "Stop"

$AppDir    = "C:\moschops"
$ConfigDir = "C:\moschops-config"
$VenvDir   = "$AppDir\.venv"
$Marker    = "$ConfigDir\.provisioned"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Add-ToPath([string]$Dir) {
    if ($env:Path -notlike "*$Dir*") {
        $env:Path = "$Dir;$env:Path"
    }
}

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Output ""
    Write-Output "=== $Name ==="
    & $Block
    Write-Output "--- $Name complete ---"
}

function Get-PgPassword {
    # Extracts the password component from DATABASE_URL (postgresql://user:pass@host:port/db)
    $uri = [uri]$DATABASE_URL
    return $uri.UserInfo.Split(':')[1]
}

function Write-EnvFile {
    # Writes a complete .env with all runtime variables. No BOM — Node.js dotenv handles it cleanly.
    $envPath = "$AppDir\backend\.env"
    $lines = @(
        "NODE_ENV=production",
        "PORT=3000",
        "DATABASE_URL=$DATABASE_URL",
        "FMP_API_KEY=$FMP_API_KEY",
        "LOG_LEVEL=info",
        "LOG_TO_FILES=true",
        "NEWS_SYNC_ENABLED=true",
        "TRAINING_PYTHON_EXECUTABLE=$VenvDir\Scripts\python.exe",
        "TRAINING_TIMEOUT_SECONDS=3600"
    )
    [System.IO.File]::WriteAllLines($envPath, $lines, (New-Object System.Text.UTF8Encoding $false))
    Write-Output "  .env written to $envPath"
}

# ── Ensure config directory exists ───────────────────────────────────────────

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# ── Fast path: already provisioned — just update code ────────────────────────

if (Test-Path $Marker) {
    Write-Output "Already provisioned. Pulling latest changes..."

    Add-ToPath "C:\ProgramData\chocolatey\bin"
    Add-ToPath "C:\Program Files\nodejs"
    Add-ToPath "C:\Program Files\Git\bin"
    Add-ToPath "C:\Program Files\PostgreSQL\16\bin"
    Add-ToPath "$env:APPDATA\npm"

    # Update repo
    $repoUrl = "https://x-access-token:$GH_PAT@github.com/$REPO.git"
    Set-Location $AppDir
    & git remote set-url origin $repoUrl 2>$null
    & git fetch origin main
    & git reset --hard origin/main

    # Regenerate .env (in case secrets changed)
    Write-EnvFile

    # Rebuild backend
    Set-Location "$AppDir\backend"
    $env:DATABASE_URL = $DATABASE_URL
    & npm.cmd ci --prefer-offline
    & npx.cmd prisma generate
    & npm.cmd run build
    & npx.cmd prisma migrate deploy

    # Restart backend NSSM service to pick up new code
    & nssm.exe restart moschops-backend
    Write-Output "Backend service restarted."

    # Update Python venv if requirements changed
    Write-Output "Updating Python venv..."
    & "$VenvDir\Scripts\pip.exe" install -r "$AppDir\training\requirements.txt" --quiet

    Write-Output "Update complete."
    exit 0
}

# ── Full first-run provisioning ───────────────────────────────────────────────

Invoke-Step "Chocolatey" {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-Expression (
        (New-Object Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1')
    )
}

Add-ToPath "C:\ProgramData\chocolatey\bin"

Invoke-Step "Install Git, Node.js LTS, NSSM, Python 3.11" {
    choco install -y git nodejs-lts nssm python --version 3.11.9 --no-progress
}

Add-ToPath "C:\Program Files\Git\bin"
Add-ToPath "C:\Program Files\nodejs"
Add-ToPath "$env:APPDATA\npm"
Add-ToPath "C:\Python311"
Add-ToPath "C:\Python311\Scripts"

Invoke-Step "Install PostgreSQL 16 with known password" {
    $pgPass = Get-PgPassword
    choco install -y postgresql16 --no-progress `
        --params "'/Password:$pgPass /NoResetPassword'"
}

Add-ToPath "C:\Program Files\PostgreSQL\16\bin"

Invoke-Step "Install Visual Studio Build Tools (for native npm modules)" {
    choco install -y visualstudio2022buildtools --no-progress `
        --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --quiet"
}

Invoke-Step "Install Visual Studio Code" {
    choco install -y vscode --no-progress
}

Add-ToPath "C:\Program Files\Microsoft VS Code\bin"

Invoke-Step "Configure PostgreSQL" {
    $pgPass = Get-PgPassword
    $env:PGPASSWORD = $pgPass

    # Create the application database (idempotent — ignore error if it already exists)
    & "C:\Program Files\PostgreSQL\16\bin\psql.exe" `
        -U postgres -h localhost `
        -c "CREATE DATABASE moschops;" 2>$null
    Write-Output "  Database 'moschops' ensured."
}

Invoke-Step "Windows Firewall — allow port 3000" {
    $existing = Get-NetFirewallRule -DisplayName "Moschops Backend" -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule `
            -DisplayName "Moschops Backend" `
            -Direction Inbound -Protocol TCP `
            -LocalPort 3000 -Action Allow -Profile Any | Out-Null
        Write-Output "  Firewall rule created."
    } else {
        Write-Output "  Firewall rule already exists."
    }
}

Invoke-Step "Clone repository" {
    $repoUrl = "https://x-access-token:$GH_PAT@github.com/$REPO.git"

    if (Test-Path $AppDir) {
        Remove-Item -Recurse -Force $AppDir
    }

    & git clone $repoUrl $AppDir
}

Invoke-Step "Write .env" {
    Write-EnvFile
}

Invoke-Step "Build backend" {
    Set-Location "$AppDir\backend"
    $env:DATABASE_URL = $DATABASE_URL

    & npm.cmd ci
    & npx.cmd prisma generate
    & npm.cmd run build
    & npx.cmd prisma migrate deploy
}

Invoke-Step "Register backend as Windows service (NSSM)" {
    $nodePath = (Get-Command node.exe).Source
    $scriptPath = "$AppDir\backend\dist\src\index.js"
    $logDir = "$AppDir\logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null

    # Remove stale registration if it exists
    & nssm.exe stop moschops-backend 2>$null
    & nssm.exe remove moschops-backend confirm 2>$null

    & nssm.exe install moschops-backend $nodePath $scriptPath
    & nssm.exe set moschops-backend AppDirectory "$AppDir\backend"
    & nssm.exe set moschops-backend AppEnvironmentExtra "NODE_ENV=production" "PORT=3000"
    & nssm.exe set moschops-backend AppStdout "$logDir\backend.log"
    & nssm.exe set moschops-backend AppStderr "$logDir\backend_error.log"
    & nssm.exe set moschops-backend AppRotateFiles 1
    & nssm.exe set moschops-backend AppRotateBytes 10485760
    & nssm.exe set moschops-backend Start SERVICE_AUTO_START
    Write-Output "  NSSM service 'moschops-backend' registered (auto-start on boot)."
}

Invoke-Step "Python venv and ML dependencies" {
    & python.exe -m venv $VenvDir
    & "$VenvDir\Scripts\pip.exe" install --upgrade pip --quiet
    & "$VenvDir\Scripts\pip.exe" install -r "$AppDir\training\requirements.txt"
    Write-Output "  Python venv ready at $VenvDir"
}

Invoke-Step "Install VS Code extensions (targets mt5admin profile)" {
    # Extensions installed to mt5admin's profile so they appear after RDP login.
    # Note: re-run 'code --install-extension <name>' from an RDP session if any fail.
    $vsixDir  = "C:\Users\mt5admin\.vscode\extensions"
    $userData = "C:\Users\mt5admin\AppData\Roaming\Code"
    New-Item -ItemType Directory -Force -Path $vsixDir  | Out-Null
    New-Item -ItemType Directory -Force -Path $userData | Out-Null
    $extensions = @(
        "ms-python.python",
        "ms-python.pylance",
        "prisma.prisma",
        "dbaeumer.vscode-eslint",
        "esbenp.prettier-vscode",
        "ms-vscode.powershell",
        "mtxr.sqltools",
        "mtxr.sqltools-driver-pg"
    )
    foreach ($ext in $extensions) {
        Write-Output "  Installing $ext..."
        & "C:\Program Files\Microsoft VS Code\bin\code.cmd" `
            --user-data-dir $userData `
            --extensions-dir $vsixDir `
            --install-extension $ext `
            --force 2>$null
    }
}

Invoke-Step "Install MT5" {
    $installer = "$env:TEMP\mt5setup.exe"

    Invoke-WebRequest `
        -Uri "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" `
        -OutFile $installer `
        -UseBasicParsing

    # /auto performs a silent install to the default location
    Start-Process -FilePath $installer -ArgumentList "/auto" -Wait -NoNewWindow

    # Run MT5 once briefly so it creates its data directories, then close it
    $mt5Exe = "C:\Program Files\MetaTrader 5\terminal64.exe"
    if (Test-Path $mt5Exe) {
        $proc = Start-Process -FilePath $mt5Exe -PassThru
        Start-Sleep -Seconds 10
        $proc | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

Invoke-Step "Write provisioned marker" {
    Set-Content -Path $Marker -Value (Get-Date -Format "o") -Encoding UTF8
}

Write-Output ""
Write-Output "Provisioning complete. Run vm-start-services.ps1 to start the backend and MT5."
