#!/usr/bin/env pwsh
# Monthly production retrain for XAUUSD D1 (gold-012 config).
#
# Strategy:
#   - Expanding window: always trains from 2012-01-01 through yesterday.
#   - Recency weighting (halflife 730 days / 2 years): bars from 2 years ago
#     get weight 0.5 vs today's bars. The model adapts to the current regime
#     without completely discarding long-term structural knowledge.
#   - Test window: last 12 months of data for gate evaluation.
#   - BOCPD regime novelty: after training, the script checks whether BOCPD
#     detected a regime break in the last 30 bars. If so, it logs a warning
#     and raises the recommended threshold by +0.03 (conservative mode).
#
# Schedule: run on the 1st of each month via Windows Task Scheduler.
#   Action: powershell.exe -File C:\moschops_01\scripts\run-monthly-retrain-gold.ps1
#
# Gate criteria for promotion (same as gold-012):
#   AUC >= 0.53  |  PF >= 1.25  |  MaxDD <= 20%  |  Trades >= 30
#
# Usage:
#   .\scripts\run-monthly-retrain-gold.ps1 [-DryRun]

param(
    [switch]$DryRun   # Print command without running
)

Set-Location C:\moschops_01

# ---------------------------------------------------------------------------
# Window: 2012-01-01 → yesterday  |  test = last 12 months
# ---------------------------------------------------------------------------
$today        = Get-Date
$trainEnd     = $today.AddDays(-1).ToString("yyyy-MM-dd")
$testStart    = $today.AddMonths(-12).ToString("yyyy-MM-01")
$testEnd      = $trainEnd
$trainStart   = "2012-01-01"
$month        = $today.ToString("yyyy-MM")
$label        = "gold-monthly-$month"

Write-Host ""
Write-Host "===== MONTHLY GOLD RETRAIN =====" -ForegroundColor Cyan
Write-Host "  Train : $trainStart -> $trainEnd"
Write-Host "  Test  : $testStart  -> $testEnd"
Write-Host "  Label : $label"
Write-Host "  Recency halflife: 730 days (2-year)"
Write-Host ""

$cmd = @(
    "training/run_historical_split.py",
    "--symbol", "XAUUSD",
    "--timeframe", "D1",
    "--train-start", $trainStart,
    "--train-end",   $trainEnd,
    "--test-start",  $testStart,
    "--test-end",    $testEnd,
    "--label-mode", "edge",
    "--min-edge-bps", "20",
    "--horizon-bars", "10",
    "--walk-forward-folds", "5",
    "--embargo-bars", "5",
    "--spread-bps", "3.0",
    "--commission-bps", "1.5",
    "--slippage-bps", "1.0",
    "--signal-variant", "baseline",
    "--cusum-event-filter",
    "--cusum-h-lookback", "20",
    "--threshold-grid", "0.44,0.45,0.46,0.47,0.48,0.49,0.50",
    "--target-max-drawdown-pct", "-25.0",
    "--sample-weight-halflife-days", "730",   # 2-year halflife → adapts to current regime
    "--run-label", $label
)

if ($DryRun) {
    Write-Host "DRY RUN — would execute:" -ForegroundColor Yellow
    Write-Host (".venv\Scripts\python.exe " + ($cmd -join " "))
    exit 0
}

$output = .venv\Scripts\python.exe @cmd 2>&1
$output | ForEach-Object { Write-Host $_ }

# ---------------------------------------------------------------------------
# Parse RESULT line
# ---------------------------------------------------------------------------
$resultLine = $output | Select-String "RESULT\s+AUC=(\S+)\s+PF=(\S+)\s+maxDD=(\S+)%\s+trades=(\d+)"
if (-not $resultLine) {
    Write-Host ""
    Write-Host "ERROR: No RESULT line found — retrain may have failed." -ForegroundColor Red
    exit 1
}

$m = $resultLine.Matches[0]
$auc    = [float]$m.Groups[1].Value
$pf     = [float]$m.Groups[2].Value
$maxdd  = [float]$m.Groups[3].Value
$trades = [int]$m.Groups[4].Value

Write-Host ""
Write-Host "===== GATE EVALUATION =====" -ForegroundColor Cyan
Write-Host "  AUC    : $auc  (gate >= 0.53)"
Write-Host "  PF     : $pf   (gate >= 1.25)"
Write-Host "  MaxDD  : $maxdd%  (gate <= 20%)"
Write-Host "  Trades : $trades  (gate >= 30)"

$pass = ($auc -ge 0.53) -and ($pf -ge 1.25) -and ($maxdd -le 20.0) -and ($trades -ge 30)

if ($pass) {
    Write-Host ""
    Write-Host "ALL GATES PASSED — model promoted for $month" -ForegroundColor Green
    Write-Host "Next step: copy ONNX model from logs to models/ and deploy to backend."
} else {
    Write-Host ""
    Write-Host "GATES FAILED — keeping previous production model." -ForegroundColor Red
    Write-Host "  Review: logs/training/*$label*/report.json"
    Write-Host "  Consider: widening threshold grid or checking for active regime break."
}

# ---------------------------------------------------------------------------
# BOCPD regime novelty check (advisory — does not block promotion)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===== BOCPD REGIME CHECK =====" -ForegroundColor Cyan
$bocpdScript = @"
import sys, json
import numpy as np
import pandas as pd
sys.path.insert(0, 'training')
from bocpd import bocpd_changepoint_probs

# Load recent bars from report (last 60 D1 bars = ~3 months)
import glob, pathlib
reports = sorted(glob.glob('logs/training/*${label}*/report.json'))
if not reports:
    print(json.dumps({'regime_break': False, 'reason': 'no report found'}))
    sys.exit(0)

data = json.loads(pathlib.Path(reports[-1]).read_text())
# Try to get close prices from the report's equity curve as a proxy
equity = data.get('equityCurve', [])
if len(equity) < 30:
    print(json.dumps({'regime_break': False, 'reason': 'insufficient equity data'}))
    sys.exit(0)

closes = np.array([e.get('equity', 0) for e in equity], dtype=float)
log_ret = np.diff(np.log(closes + 1e-9))
cp = bocpd_changepoint_probs(log_ret[-60:], hazard_lambda=60)
recent_max = float(np.nanmax(cp[-30:])) if len(cp) >= 30 else 0.0
regime_break = recent_max > 0.70
print(json.dumps({'regime_break': regime_break, 'max_cp_prob': round(recent_max, 3)}))
"@

$bocpdResult = .venv\Scripts\python.exe -c $bocpdScript 2>&1 | Select-String "^\{" | Select-Object -Last 1
if ($bocpdResult) {
    $b = $bocpdResult.Line | ConvertFrom-Json
    if ($b.regime_break) {
        Write-Host "  WARNING: BOCPD detected regime break (prob=$($b.max_cp_prob))" -ForegroundColor Yellow
        Write-Host "  Recommended: raise live threshold by +0.03 for next 20 bars."
        Write-Host "  Rationale: model may need 1-2 months of new data to fully adapt."
    } else {
        Write-Host "  No regime break detected (max_cp_prob=$($b.max_cp_prob))" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Retrain complete: $label" -ForegroundColor Cyan
