# Azure VM Deployment LLD — MT5 + Backend Single-VM

**Document:** `docs/02-architecture/lld_azure_vm.md`
**Version:** 1.1
**Status:** Draft
**Date:** 2026-05-28
**Change (v1.1):** Added VS Code developer environment, Python 3.11 ML stack, Docker Desktop (Phase 2), container migration path section.
**Related files:**
- `.github/workflows/mt5-vm.yml`
- `scripts/vm-provision.ps1`
- `scripts/vm-start-services.ps1`

---

## Contents

- [1. Purpose and Scope](#1-purpose-and-scope)
- [2. Architecture Overview](#2-architecture-overview)
- [3. Azure Resource Inventory](#3-azure-resource-inventory)
- [4. VM Software Stack](#4-vm-software-stack)
- [5. Network Design](#5-network-design)
- [6. Service Topology](#6-service-topology)
- [7. Environment Configuration](#7-environment-configuration)
- [8. Startup and Deployment Sequence](#8-startup-and-deployment-sequence)
- [9. Known Gaps and Required Fixes](#9-known-gaps-and-required-fixes)
- [10. Recommended Enhancements](#10-recommended-enhancements)
- [11. Recovery Procedures](#11-recovery-procedures)
- [12. Container Migration Path](#12-container-migration-path)

---

## 1. Purpose and Scope

This document describes the low-level design for the single-VM Azure deployment that runs the MetaTrader 5 (MT5) terminal and the Node.js Fastify backend on the same Windows host.

**Why a single VM?**  
The MT5 Expert Advisor (`DailyBreakoutEA.mq5`) calls the backend at `http://127.0.0.1:3000`. Running both processes on the same machine is the simplest path to satisfying that constraint without changing the EA or introducing a reverse proxy.

**In scope:**
- Azure resource design (VM, NSG, public IP, resource group)
- Windows VM software stack (PostgreSQL, Node.js, MT5, Python ML stack, VS Code, Docker)
- GitHub Actions workflow for lifecycle management (start / stop / status)
- Secrets and configuration management
- Service topology and startup sequence
- Developer access setup (VS Code via RDP)
- Python ML training environment (scikit-learn, XGBoost, LightGBM, ONNX pipeline)
- Known gaps and their fixes
- Container migration path (Phase 2 evolution)

**Out of scope:**
- Multi-VM / AKS deployment (see `lld_v2.md` §6)
- Azure Database for PostgreSQL migration (v2.1 work)
- SSL/TLS termination
- Continuous delivery beyond the manual workflow

**Setup phases:**
- **Phase 1 — Automated (GitHub Actions):** All software that does not require a VM reboot. Installed by `vm-provision.ps1` on first `start` run.
- **Phase 2 — One-time manual (RDP session):** Docker Desktop + WSL2, which require a reboot after installation. Performed once by the developer after the first successful Phase 1 run.

---

## 2. Architecture Overview

```
┌──────────────────────────────────┐   ┌──────────────────────────────┐
│  GitHub Actions (ubuntu runner)  │   │  Developer (RDP session)     │
│                                  │   │                              │
│  workflow_dispatch               │   │  VS Code + extensions        │
│  start | stop | status           │   │  Python ML experiments       │
│  az vm run-command (PowerShell)  │   │  psql, node, git             │
└──────────────┬───────────────────┘   └──────────────┬───────────────┘
               │                                      │ RDP :3389
               ▼  Azure Resource Group: rg-moschops-mt5  (uksouth)
┌─────────────────────────────────────────────────────────────────────┐
│  Virtual Network + NSG                                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  VM: vm-moschops-mt5    Standard_B2ms — 2 vCPU / 8 GB RAM    │  │
│  │  OS: Windows Server 2022 Datacenter                           │  │
│  │                                                               │  │
│  │  ┌─────────────────┐  ┌──────────────────┐                   │  │
│  │  │  PostgreSQL 16  │  │  Fastify Backend │  Windows service  │  │
│  │  │  :5432 (local)  │◄─│  :3000  (NSSM)   │  (NSSM)          │  │
│  │  └─────────────────┘  └────────┬─────────┘                   │  │
│  │                                │ 127.0.0.1:3000               │  │
│  │                       ┌────────▼──────────┐                   │  │
│  │                       │  MT5 terminal     │  Task Scheduler   │  │
│  │                       │  DailyBreakoutEA  │                   │  │
│  │                       └────────┬──────────┘                   │  │
│  │                                │ HTTPS to broker               │  │
│  │  ┌──────────────────────────┐  │                               │  │
│  │  │  Python 3.11 + .venv     │  │                               │  │
│  │  │  scikit-learn, XGBoost   │  │                               │  │
│  │  │  LightGBM, skl2onnx      │  │  (training runs, not live)   │  │
│  │  └──────────────────────────┘  │                               │  │
│  │                                │                               │  │
│  │  ┌──────────────────────────┐  │                               │  │
│  │  │  Docker Desktop (Ph. 2)  │  │                               │  │
│  │  │  WSL2 + Ubuntu 22.04     │  │  (containers, future use)    │  │
│  │  └──────────────────────────┘  │                               │  │
│  └────────────────────────────────┼───────────────────────────────┘  │
│                                   │                                   │
└───────────────────────────────────┼───────────────────────────────────┘
                                    ▼
                           Broker (e.g. MetaQuotes Demo)
```

**Key design choices:**

| Choice | Rationale |
|---|---|
| Single VM | EA hard-codes `127.0.0.1:3000`; avoids network config changes |
| Windows Server 2022 | Required for MT5 (Windows-only application) |
| Standard_B2ms | Burstable; sufficient for MT5 + Node + PG + Python ML; ~£35/month running, ~£1.50/month deallocated |
| PostgreSQL 16 native install (Phase 1) | No reboot required; simpler for first-run automation |
| Docker Desktop (Phase 2 manual) | Mirrors the laptop dev environment; enables future container migration |
| Python 3.11 + venv | Matches the local ML training stack exactly; enables model training and ONNX export on the VM |
| VS Code installed on VM | Developer can RDP in and work directly on the VM as a full dev environment |
| Deallocate on stop | Preserves OS disk, DB data, and .venv; stops compute billing |
| Manual trigger only | Live trading should never start autonomously |

---

## 3. Azure Resource Inventory

| Resource | Name | Type | Notes |
|---|---|---|---|
| Resource Group | `rg-moschops-mt5` | Microsoft.Resources/resourceGroups | Region: uksouth |
| Virtual Machine | `vm-moschops-mt5` | Microsoft.Compute/virtualMachines | Win2022Datacenter, Standard_B2ms |
| OS Disk | auto-named | Premium SSD | 128 GB |
| Public IP | auto-named | Standard SKU | **Dynamic by default** — see §10 for static IP recommendation |
| Virtual Network | auto-named | Microsoft.Network/virtualNetworks | Default /16 CIDR |
| Network Security Group | auto-named | Microsoft.Network/networkSecurityGroups | Rules defined in §5 |
| NIC | auto-named | Microsoft.Network/networkInterfaces | Attached to VM |

**Service principal (for GitHub Actions):**  
A dedicated SP with `Contributor` role scoped to `rg-moschops-mt5` only.  
Create with:
```bash
az ad sp create-for-rbac \
  --name sp-moschops-gh-actions \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-moschops-mt5 \
  --sdk-auth
```
Store the JSON output as the `AZURE_CREDENTIALS` GitHub secret.

---

## 4. VM Software Stack

### Phase 1 — Automated (installed by vm-provision.ps1)

All items below are installed on the first `start` run via Chocolatey and do not require a VM reboot.

| Component | Version | Install method | Purpose |
|---|---|---|---|
| Chocolatey | latest | PowerShell bootstrap | Package manager |
| Git | latest | `choco install git` | Clone / pull repo |
| Node.js | LTS (20.x) | `choco install nodejs-lts` | Backend runtime |
| npm | bundled with Node | — | Dependency management |
| PostgreSQL | 16 | `choco install postgresql16` | Application database |
| NSSM | 2.24 | `choco install nssm` | Run backend as a Windows service |
| Python | 3.11.x | `choco install python311` | ML training pipeline runtime |
| Visual Studio Build Tools | 2022 | `choco install visualstudio2022buildtools` | Native npm modules (onnxruntime-node) |
| VS Code | latest | `choco install vscode` | IDE for development via RDP |
| MetaTrader 5 | latest | Downloaded from MetaQuotes CDN | Trading terminal |

**Python ML packages** (installed into `C:\moschops\.venv` via pip from `training/requirements.txt`):

| Package | Version | Purpose |
|---|---|---|
| pandas | 2.2.3 | Data manipulation |
| numpy | 2.2.2 | Numerical computation |
| scikit-learn | 1.6.1 | Core ML estimators |
| xgboost | 2.1.4 | Gradient boosting estimator |
| lightgbm | 4.5.0 | Gradient boosting estimator |
| onnx | 1.17.0 | ONNX model format |
| skl2onnx | 1.18.0 | scikit-learn → ONNX export |
| psycopg[binary] | 3.2.4 | PostgreSQL driver (training scripts) |
| SQLAlchemy | 2.0.37 | ORM for training data access |
| python-dotenv | 1.0.1 | Load .env in training scripts |

**VS Code extensions** (installed during Phase 1 provisioning):

| Extension ID | Purpose |
|---|---|
| `ms-python.python` | Python language support |
| `ms-python.pylance` | Python type checking |
| `prisma.prisma` | Prisma schema formatting |
| `dbaeumer.vscode-eslint` | ESLint integration |
| `esbenp.prettier-vscode` | Code formatter |
| `ms-vscode.powershell` | PowerShell editing |
| `mtxr.sqltools` | SQL query runner (connect to local PostgreSQL) |
| `mtxr.sqltools-driver-pg` | PostgreSQL driver for SQLTools |

### Phase 2 — Manual one-time RDP session

These require a reboot and must be installed manually after the first successful Phase 1 run.

| Component | Version | Install method | Purpose |
|---|---|---|---|
| WSL2 | built-in | `wsl --install -d Ubuntu-22.04` | Linux kernel for Docker |
| Docker Desktop | latest | `choco install docker-desktop` (then reboot) | Container runtime for future migration |

> After installing Docker Desktop, enable the WSL2 backend in Docker Desktop settings. The `docker compose up -d` command in the repo root will then start PostgreSQL in a container (matching the local laptop setup exactly) — at which point the native PostgreSQL service can be stopped if desired.

---

**Disk layout on VM:**

```
C:\moschops\                         ← Git repo (clone root)
  backend\
    .env                             ← Written by provision script (not committed)
    dist\                            ← TypeScript build output
    prisma\
    logs\
  mql5\
    Experts\DailyBreakoutEA.mq5
  models\
    daily_breakout_model.onnx
  training\
    requirements.txt
    train_walk_forward.py
    run_historical_split.py
  validation\
    backtest_engine.py
  .venv\                             ← Python virtual environment (created by provision)
    Scripts\python.exe
    Scripts\pip.exe

C:\moschops-config\
  .provisioned                       ← Marker file; existence = provisioning done

C:\Program Files\MetaTrader 5\
  terminal64.exe
  metaeditor64.exe

C:\Program Files\Microsoft VS Code\
  Code.exe

%APPDATA%\MetaQuotes\Terminal\<INSTANCE_ID>\
  MQL5\Experts\
    DailyBreakoutEA.mq5              ← Copied from repo on every start
    DailyBreakoutEA.ex5             ← Compiled by MetaEditor (see §9.6)
```

---

## 5. Network Design

### Azure NSG rules (inbound)

| Priority | Name | Port | Protocol | Source | Action | Purpose |
|---|---|---|---|---|---|---|
| 1000 | RDP | 3389 | TCP | * | Allow | Remote Desktop access |
| 1100 | Backend | 3000 | TCP | * | Allow | Backend health checks from external monitoring |
| 65000 | AllowVNetInBound | Any | Any | VirtualNetwork | Allow | Azure default |
| 65500 | DenyAllInBound | Any | Any | * | Deny | Azure default |

> **Security note:** Port 3389 (RDP) is open to `*` by default from `az vm create`. Restrict this to your static IP address after initial setup:
> ```bash
> az network nsg rule update \
>   --resource-group rg-moschops-mt5 \
>   --nsg-name <nsg-name> \
>   --name default-allow-rdp \
>   --source-address-prefixes <YOUR_IP>/32
> ```

### Windows Firewall rules (inside the VM)

Azure NSG rules alone are not sufficient — Windows Firewall also applies and blocks inbound traffic by default.

**Required rule (must be added in provision script):**
```powershell
New-NetFirewallRule `
  -DisplayName "Moschops Backend" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 3000 `
  -Action Allow `
  -Profile Any
```

This is currently **missing from vm-provision.ps1** — see §9.

---

## 6. Service Topology

### PostgreSQL 16

- **Install:** Chocolatey `postgresql16` package
- **Service name:** `postgresql-x64-16` (Windows service, auto-start)
- **Port:** 5432 (loopback only — not exposed externally)
- **Superuser:** `postgres`
- **Database:** `moschops`
- **Password:** Set via provision script using `psql -c "ALTER USER postgres PASSWORD '...'"` with the value extracted from `DATABASE_URL`

**Known issue with Chocolatey postgres install:** The package creates a Windows service running as the `postgres` OS user. The first `psql` connection must use Windows trust authentication or the initial random password. See §9 for the correct fix.

### Fastify Backend

- **Source:** `C:\moschops\backend\dist\src\index.js`
- **Start command:** `node dist\src\index.js`
- **Port:** 3000
- **Process manager:** NSSM service `moschops-backend` (auto-restart, auto-start on boot) — **not yet implemented, see §9**
- **Logs:** `C:\moschops\backend\logs\` (controlled by `LOG_DIR` env var)
- **Health endpoint:** `GET /health` → 200 OK when backend and DB are ready

### MT5 Terminal

- **Executable:** `C:\Program Files\MetaTrader 5\terminal64.exe`
- **Launch args:** `/Login:<n> /Password:<p> /Server:<s>`
- **EA location:** `%APPDATA%\MetaQuotes\Terminal\<ID>\MQL5\Experts\DailyBreakoutEA.ex5`
- **EA config:** `InpApiBase = "http://127.0.0.1:3000"` (hardcoded default in source)
- **Auto-start:** Task Scheduler entry (recommended — see §9.7)

### Python ML Training Pipeline

- **Runtime:** `C:\moschops\.venv\Scripts\python.exe`
- **Key scripts:**
  - `training/run_historical_split.py` — gate-quality walk-forward runs
  - `training/train_walk_forward.py` — prototyping / quick experiments
  - `validation/backtest_engine.py` — backtest evaluation
- **Output:** `models/daily_breakout_model.onnx` + `models/feature_schema_v1.json`
- **Database access:** Training scripts connect directly to PostgreSQL using `DATABASE_URL` from `.env`
- **Backend integration:** After a successful training run, the new `.onnx` file is placed in `models/`. The backend reloads the model on restart (or via a future hot-reload endpoint).
- **Not a live service:** Training runs are initiated manually via VS Code terminal or PowerShell. They do not run automatically alongside the backend.

### Docker (Phase 2 — installed manually)

- **Purpose:** Container runtime for future migration of backend and PostgreSQL to containers
- **Current use:** Optional — can replace the native PostgreSQL service with `docker compose up -d` (matches local laptop setup exactly)
- **Future use:** Full containerized stack as per `lld_v2.md` §6

---

## 7. Environment Configuration

The backend validates environment variables at startup via Zod (`src/utils/env.ts`). The provision script must write these to `C:\moschops\backend\.env`.

### Required in `.env`

| Variable | Example value | Source |
|---|---|---|
| `NODE_ENV` | `production` | Hardcoded in provision script |
| `PORT` | `3000` | Hardcoded in provision script |
| `DATABASE_URL` | `postgresql://postgres:<pw>@localhost:5432/moschops` | `DATABASE_URL` GitHub secret |

### Optional but strongly recommended

| Variable | Example value | Source |
|---|---|---|
| `FMP_API_KEY` | `abc123xyz` | `FMP_API_KEY` GitHub secret |
| `LOG_LEVEL` | `info` | Hardcoded in provision script |
| `LOG_TO_FILES` | `true` | Hardcoded |
| `LOG_DIR` | `logs` | Hardcoded |
| `NEWS_SYNC_ENABLED` | `true` | Hardcoded |
| `NEWS_PROVIDER_TIER` | `FREE` | Hardcoded (or BASIC) |
| `TRAINING_PYTHON_EXECUTABLE` | `C:\moschops\.venv\Scripts\python.exe` | Hardcoded in provision script |
| `TRAINING_TIMEOUT_SECONDS` | `600` | Hardcoded |

### Current `.env` written by vm-provision.ps1

```
DATABASE_URL=<value>
```

**Gap:** Only `DATABASE_URL` is written. `NODE_ENV`, `PORT`, and `FMP_API_KEY` are missing. The backend will fall back to defaults for most, but `NODE_ENV=development` will be assumed, which enables debug logging and may suppress some production behaviours. See §9.

### Additional GitHub secret to add

| Secret | Description |
|---|---|
| `FMP_API_KEY` | Financial Modeling Prep API key (needed for news sync) |

---

## 8. Startup and Deployment Sequence

### First run (VM creation)

```
GitHub Actions trigger (action=start)
  │
  ├─ az group create
  ├─ az vm create                           ← ~5 min
  ├─ az vm open-port 3000
  │
  ├─ vm-provision.ps1                       ← ~40-50 min total (Phase 1)
  │    ├─ Check marker → not found → full install
  │    ├─ Install Chocolatey
  │    ├─ choco install git nodejs-lts postgresql16 nssm
  │    ├─           python311 visualstudio2022buildtools vscode
  │    ├─ Add Windows Firewall rule for port 3000
  │    ├─ Configure PostgreSQL password and create moschops database
  │    ├─ git clone repo
  │    ├─ npm ci
  │    ├─ npx prisma generate
  │    ├─ npm run build
  │    ├─ npx prisma migrate deploy
  │    ├─ Write C:\moschops\backend\.env (all required vars incl. FMP_API_KEY)
  │    ├─ python -m venv C:\moschops\.venv
  │    ├─ .venv\Scripts\pip install -r training\requirements.txt
  │    ├─ Install VS Code extensions (code --install-extension ...)
  │    ├─ Install MT5 silently (/auto)
  │    ├─ First MT5 launch (creates data directories), then close
  │    └─ Write C:\moschops-config\.provisioned
  │
  ├─ vm-start-services.ps1
  │    ├─ Kill stale node / terminal64 processes
  │    ├─ Register backend as NSSM service (idempotent)
  │    ├─ nssm restart moschops-backend
  │    ├─ Wait for /health (up to 30s)
  │    ├─ Copy DailyBreakoutEA.mq5 to MT5 Experts folder
  │    ├─ Compile EA with metaeditor64.exe /compile
  │    └─ Start MT5 with /Login /Password /Server
  │
  └─ Print public IP and health URL

──────────────────────────────────────────────────────────────
 Phase 2 — manual (one-time RDP session, done once after Phase 1 completes)
──────────────────────────────────────────────────────────────

RDP to <PUBLIC_IP> as mt5admin
  │
  ├─ wsl --install -d Ubuntu-22.04       ← requires reboot
  ├─ [reboot via Azure portal or az vm restart]
  ├─ RDP back in after reboot
  ├─ choco install docker-desktop
  ├─ [reboot]
  ├─ Open Docker Desktop, enable WSL2 backend, accept license
  └─ Optionally: docker compose up -d     ← starts PG in container
               net stop postgresql-x64-16  ← stop native PG if switching
```

### Subsequent runs (VM already provisioned)

```
GitHub Actions trigger (action=start)
  │
  ├─ az vm start             ← ~2 min
  ├─ az vm open-port (idempotent)
  │
  ├─ vm-provision.ps1
  │    ├─ Check marker → found → fast path
  │    ├─ git pull origin main
  │    ├─ npm ci + npx prisma generate
  │    ├─ npm run build + prisma migrate deploy
  │    └─ pip install -r training\requirements.txt (idempotent, fast if unchanged)
  │
  └─ vm-start-services.ps1  (same as first run)
```

### Stop

```
GitHub Actions trigger (action=stop)
  │
  └─ az vm deallocate        ← ~1 min
       Disk preserved, PostgreSQL data preserved, billing stops
```

---

## 9. Known Gaps and Required Fixes

All gaps listed below have been resolved in the current scripts (`vm-provision.ps1`, `vm-start-services.ps1`, and `mt5-vm.yml`) as of the May 2026 update. This section is retained for historical traceability.

### 9.1 PostgreSQL password configuration ~~(Critical)~~ — **RESOLVED**

**Problem:** Chocolatey's `postgresql16` package creates the `postgres` Windows OS user and PostgreSQL superuser with a **randomly generated password**. The provision script cannot log in with `psql -U postgres` without first knowing this password.

**Fix:** Pass the desired password as a Chocolatey install parameter, then use `pg_hba.conf` trust mode as a fallback if needed:
```powershell
choco install postgresql16 -y --params "'/Password:$pg_pass /NoResetPassword'"
```
Where `$pg_pass` is the password component extracted from `$DATABASE_URL`. The provision script already parses this; it just needs to be passed to Chocolatey.

### 9.2 `prisma generate` missing before build ~~(Critical)~~ — **RESOLVED**

**Problem:** `npm run build` (TypeScript compile) will fail because the Prisma client types in `node_modules/.prisma/client` are not generated until `npx prisma generate` runs.

**Fix:** Add `npx prisma generate` between `npm ci` and `npm run build` in `vm-provision.ps1`.

### 9.3 Windows Firewall rule for port 3000 ~~(Critical)~~ — **RESOLVED**

**Problem:** Azure NSG opens port 3000 at the Azure network boundary, but Windows Firewall (inside the VM) blocks all inbound connections on port 3000 by default. The backend will not be reachable externally.

**Fix:** Add to `vm-provision.ps1`:
```powershell
New-NetFirewallRule `
  -DisplayName "Moschops Backend" `
  -Direction Inbound -Protocol TCP `
  -LocalPort 3000 -Action Allow -Profile Any
```

### 9.4 Incomplete `.env` file ~~(High)~~ — **RESOLVED**

**Problem:** The provision script writes only `DATABASE_URL` to `C:\moschops\backend\.env`. The backend will start with `NODE_ENV=development` and without `FMP_API_KEY`, causing news sync to fail.

**Fix:** Expand the `Set-Content` block in `vm-provision.ps1` to include:
```
NODE_ENV=production
PORT=3000
DATABASE_URL=<value>
FMP_API_KEY=<value>
LOG_LEVEL=info
LOG_TO_FILES=true
NEWS_SYNC_ENABLED=true
```
Add `FMP_API_KEY` as a GitHub secret and pass it to the provision script as a fourth parameter.

### 9.5 Backend not running as a Windows service ~~(High)~~ — **RESOLVED**

**Problem:** `Start-Process` in `vm-start-services.ps1` starts `node.exe` as a plain process. If the process crashes or the VM reboots, the backend stays down until the workflow is manually re-triggered.

**Fix:** Use NSSM (already flagged for install in §4) to register the backend as a Windows service:
```powershell
# Register (idempotent)
nssm install moschops-backend "C:\Program Files\nodejs\node.exe" `
    "C:\moschops\backend\dist\src\index.js"
nssm set moschops-backend AppDirectory "C:\moschops\backend"
nssm set moschops-backend AppEnvironmentExtra `
    "NODE_ENV=production" "PORT=3000"
nssm set moschops-backend Start SERVICE_AUTO_START

# Start / restart
nssm restart moschops-backend
```

### 9.6 MT5 EA not compiled ~~(High)~~ — **RESOLVED**

**Problem:** `vm-start-services.ps1` copies `DailyBreakoutEA.mq5` (source) to the MT5 Experts folder. MT5 needs the compiled `DailyBreakoutEA.ex5` to run the EA. Without compilation, the EA will not appear in the Navigator or attach to a chart.

**Fix:** Add a compilation step using MetaEditor's command-line compile flag:
```powershell
$metaEditor = "C:\Program Files\MetaTrader 5\metaeditor64.exe"
$expertDir  = "<MT5_DATA>\MQL5\Experts"
Start-Process -FilePath $metaEditor `
    -ArgumentList "/compile:`"$expertDir\DailyBreakoutEA.mq5`" /log" `
    -Wait -NoNewWindow
```

### 9.7 MT5 does not auto-start after VM reboot ~~(Medium)~~ — **RESOLVED**

**Problem:** MT5 is launched via `Start-Process` at workflow time only. If the VM reboots (e.g. after a Windows Update), MT5 will not restart automatically.

**Fix:** Register MT5 as a Task Scheduler entry running at user logon:
```powershell
$action  = New-ScheduledTaskAction -Execute $MT5Exe `
               -Argument "/Login:$MT5_LOGIN /Password:$MT5_PASSWORD /Server:$MT5_SERVER"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "MT5 AutoStart" `
    -Action $action -Trigger $trigger -RunLevel Highest -Force
```

### 9.8 Dynamic public IP changes on deallocate ~~(Low)~~ — **RESOLVED**

**Problem:** The VM's public IP is allocated dynamically. After `az vm deallocate` + `az vm start`, the IP address changes. Any monitoring URLs or firewall allowlists pointing to the old IP will break.

**Fix:** Allocate a static (Standard SKU) public IP and associate it at VM creation. Add to the `az vm create` step:
```bash
az network public-ip create \
  --resource-group rg-moschops-mt5 \
  --name pip-moschops-mt5 \
  --sku Standard \
  --allocation-method Static
```
Then reference `--public-ip-address pip-moschops-mt5` in `az vm create`.

### 9.9 Visual Studio Build Tools for onnxruntime-node ~~(Low)~~ — **RESOLVED**

**Problem:** `onnxruntime-node` ships prebuilt binaries for Node 20 on Windows x64 and will not require build tools under normal conditions. However, if npm falls back to building from source (e.g. mismatched Node ABI version), the build will fail without MSVC.

**Fix (precautionary):** Add to Chocolatey installs:
```powershell
choco install visualstudio2022buildtools -y --no-progress `
    --package-parameters "--add Microsoft.VisualStudio.Workload.VCTools"
```

---

## 10. Recommended Enhancements

These are not blockers but are recommended before using the VM in a live trading context.

| Enhancement | Why | Effort |
|---|---|---|
| Static public IP (§9.8) | Stable address for monitoring and allowlisting | Low |
| Restrict RDP to your IP | Reduces attack surface significantly | Low |
| Azure auto-shutdown schedule | Prevents accidental 24/7 billing if workflow stop is missed | Low |
| NSSM for backend (§9.5) | Crash recovery without re-running the workflow | Medium |
| MT5 Task Scheduler entry (§9.7) | Survive VM reboots without re-running the workflow | Medium |
| Azure Monitor + Log Analytics | Alert on VM CPU/memory and backend health | Medium |
| Backend logs forwarded to Azure Monitor | Persistent, searchable logs outside the VM disk | Medium |
| Secrets via Azure Key Vault + Managed Identity | Remove secrets from GitHub and Azure Activity Logs | High |

### Azure Key Vault (recommended for production)

Currently secrets (`MT5_PASSWORD`, `DATABASE_URL`, `GH_PAT`) are passed via `az vm run-command invoke --parameters`. These values appear in **Azure Activity Logs** (retention: 90 days).

Hardened approach:
1. Enable System-assigned Managed Identity on the VM
2. Store all secrets in Azure Key Vault
3. Grant the VM's identity `Key Vault Secrets User` on the vault
4. Provision script fetches secrets directly: `az keyvault secret show --vault-name kv-moschops --name DB-URL --query value -o tsv`
5. No secrets in `--parameters` or GitHub workflow env

---

## 11. Recovery Procedures

### Backend crashes

If NSSM is installed (§9.5): auto-restarts within seconds with no action required.  
If using `Start-Process`: re-run the workflow with `action=start`. The provision script detects the marker file and goes straight to `npm run build` + service start.

### VM reboots unexpectedly

- PostgreSQL: starts automatically (Windows service).
- Backend: starts automatically if NSSM is configured (§9.5).
- MT5: starts automatically if Task Scheduler entry is configured (§9.7).
- Otherwise: re-run workflow with `action=start`.

### Database corrupted or migration failed

1. Connect via RDP to the VM.
2. Run `psql -U postgres` to inspect the DB state.
3. To reset: `DROP DATABASE moschops;` then re-run the workflow (provision detects marker and re-runs migrations only).

### VM disk corrupted / VM deleted

1. Re-run the workflow with `action=start` — the VM does not exist so full provisioning runs automatically.
2. The database is rebuilt from scratch; all live trade history is lost.
3. **Mitigation:** Enable Azure Backup for the VM OS disk (not configured by default).

### EA stops trading (backend unreachable)

1. Run `action=status` to confirm VM is running.
2. Check `/health`: `curl http://<IP>:3000/health`
3. If 5xx: check `C:\moschops\backend\logs\` via RDP.
4. If no response: backend process is dead. Re-run `action=start`.

---

## 12. Container Migration Path

This section documents the planned evolution from the current single-VM flat install to a containerized stack, as referenced in `lld_v2.md` §6.

### Current state (Phase 1 VM)

Everything runs as native Windows processes on a single VM:

```
Windows Server 2022
  postgresql-x64-16   (Windows service)
  moschops-backend    (NSSM Windows service)
  terminal64.exe      (Task Scheduler, GUI app)
  python.exe          (interactive / manual runs)
```

### Target state (Phase 2 / v2.1 containers)

Each service runs in its own container. MT5 remains on Windows but is isolated in its own VM or container with GPU-optional support.

```
Docker Compose (or AKS) on the same VM initially, then split later:

  postgres:16          (Linux container via WSL2 / Docker Desktop)
  moschops-backend     (Linux container — Node 20 Alpine)
  moschops-training    (Linux container — Python 3.11 slim)

  MT5 (Windows-only)
    \u2514 remains as a native Windows process on the same VM
       OR moves to a separate dedicated Windows VM
       communicating with the backend via HTTP (not 127.0.0.1)
```

### Migration steps

| Step | Action | Risk | When |
|---|---|---|---|
| 1 | Install Docker Desktop + WSL2 (Phase 2 manual step) | Low | After first successful Phase 1 run |
| 2 | Run `docker compose up -d` for PostgreSQL only | Low | Confirms Docker networking works |
| 3 | Stop native PostgreSQL service; verify backend reconnects | Medium | After data migration / pg_dump \u2192 restore |
| 4 | Containerize backend: build `backend/Dockerfile`, add to `docker-compose.yml` | Medium | When backend is stable |
| 5 | Containerize training pipeline: `training/Dockerfile` | Low | Can be done independently |
| 6 | Move MT5 to its own dedicated VM or keep co-located | Medium | Depends on EA latency requirements |
| 7 | Migrate to Azure Container Apps or AKS (v2.1) | High | After all containers are proven locally |

### EA connectivity after containerization

When the backend moves from `127.0.0.1:3000` to a container or separate host, the EA's `InpApiBase` input parameter must be updated. The EA already exposes this as a configurable input:

```mql5
input string InpApiBase = "http://127.0.0.1:3000";
```

Update this to the container's host IP or domain name when the backend is no longer co-located. No code change is required — only an MT5 EA settings update.

### Dockerfile sketches (for future use)

**backend/Dockerfile:**
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY backend/package*.json ./
RUN npm ci --omit=dev
COPY backend/dist ./dist
COPY backend/prisma ./prisma
COPY models ./models
ENV NODE_ENV=production PORT=3000
EXPOSE 3000
CMD ["node", "dist/src/index.js"]
```

**training/Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY training/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY training ./training
COPY validation ./validation
COPY models ./models
CMD ["python", "training/run_historical_split.py"]
```
