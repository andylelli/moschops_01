#!/usr/bin/env pwsh
# Rolling walk-forward test for XAUUSD D1 — 5-year train window
# Train 5 years, test 1 year, step 1 year, 2012 -> 2025
# Motivation: 3yr windows leave some windows with <200 CUSUM events; 5yr
# roughly doubles the training data and resolves the 2017 0-trade issue.
#
# Parameters:
#   -WeightHalflifeDays : recency halflife in days (0 = uniform, 730 = 2yr halflife)
#   -LabelPrefix        : prefix for run labels (default "rwf-5yr")
param(
    [int]$WeightHalflifeDays = 730,
    [string]$LabelPrefix = "rwf-5yr"
)

Set-Location C:\moschops_01

$trainYears  = 5
$testYears   = 1
$stepYears   = 1
$startYear   = 2012   # earliest XAUUSD D1 data
$endTestYear = 2025   # last complete test year

$results = @()

$year = $startYear
while (($year + $trainYears + $testYears - 1) -le ($endTestYear + $testYears - 1)) {
    $trainStart = "$year-01-01"
    $trainEnd   = "$($year + $trainYears - 1)-12-31"
    $testStart  = "$($year + $trainYears)-01-01"
    $testEnd    = "$($year + $trainYears + $testYears - 1)-12-31"
    $label      = "$LabelPrefix-$($year)-$($year + $trainYears - 1)"

    Write-Host ""
    Write-Host "=== Window: train $trainStart -> $trainEnd  |  test $testStart -> $testEnd ===" -ForegroundColor Cyan

    $extraArgs = @()
    if ($WeightHalflifeDays -gt 0) {
        $extraArgs += "--sample-weight-halflife-days"
        $extraArgs += "$WeightHalflifeDays"
    }

    $output = .venv\Scripts\python.exe training/run_historical_split.py `
        --symbol XAUUSD --timeframe D1 `
        --train-start $trainStart --train-end $trainEnd `
        --test-start  $testStart  --test-end  $testEnd `
        --label-mode edge --min-edge-bps 20 --horizon-bars 10 `
        --walk-forward-folds 3 --embargo-bars 5 --min-fold-train-rows 60 --min-fold-val-rows 30 `
        --spread-bps 3.0 --commission-bps 1.5 --slippage-bps 1.0 `
        --signal-variant baseline `
        --cusum-event-filter --cusum-h-lookback 20 `
        --threshold-grid "0.45,0.46,0.47,0.48,0.49,0.50" `
        --target-max-drawdown-pct -25.0 `
        --single-train-window `
        @extraArgs `
        --run-label $label 2>&1

    $resultLine = $output | Select-String "RESULT"
    Write-Host $resultLine -ForegroundColor Yellow
    $results += "$($year + $trainYears)  $resultLine"

    $year += $stepYears
}

Write-Host ""
Write-Host "===== XAUUSD D1 ROLLING WF SUMMARY - 5yr train (halflife=${WeightHalflifeDays}d) =====" -ForegroundColor Green
Write-Host "Year  Result"
$results | ForEach-Object { Write-Host $_ }
