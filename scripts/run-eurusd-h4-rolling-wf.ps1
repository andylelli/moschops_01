#!/usr/bin/env pwsh
# Rolling walk-forward test for EURUSD H4
# Train 4 years, test 1 year, step 1 year, 2014 -> 2026
#
# Parameters:
#   -WeightHalflifeDays : recency halflife in days (0 = uniform, 730 = 2yr halflife)
#   -LabelPrefix        : prefix for run labels (default "rwf-eur-h4")
param(
    [int]$WeightHalflifeDays = 730,
    [string]$LabelPrefix = "rwf-eur-h4"
)

Set-Location C:\moschops_01

$trainYears = 4
$stepYears  = 1
$startYear  = 2014
$today      = [datetime]::Today.ToString('yyyy-MM-dd')

$results = @()

$year = $startYear
while ($true) {
    $trainStart = "$year-01-01"
    $trainEnd   = "$($year + $trainYears - 1)-12-31"
    $testStart  = "$($year + $trainYears)-01-01"
    $testEndRaw = "$($year + $trainYears)-12-31"

    # Cap test end at today for the current (partial) year
    $testEnd = if ([datetime]$testEndRaw -gt [datetime]$today) { $today } else { $testEndRaw }

    # Stop if the test window starts after today
    if ([datetime]$testStart -gt [datetime]$today) { break }

    $label = "$LabelPrefix-$year-$($year + $trainYears - 1)"

    Write-Host ""
    Write-Host "=== Window: train $trainStart -> $trainEnd  |  test $testStart -> $testEnd ===" -ForegroundColor Cyan

    $extraArgs = @()
    if ($WeightHalflifeDays -gt 0) {
        $extraArgs += "--sample-weight-halflife-days"
        $extraArgs += "$WeightHalflifeDays"
    }

    $output = .venv\Scripts\python.exe training/run_historical_split.py `
        --symbol EURUSD --timeframe H4 `
        --train-start $trainStart --train-end $trainEnd `
        --test-start  $testStart  --test-end  $testEnd `
        --label-mode edge --min-edge-bps 8 --horizon-bars 8 `
        --walk-forward-folds 3 --embargo-bars 5 `
        --min-fold-train-rows 100 --min-fold-val-rows 50 `
        --spread-bps 2.5 --commission-bps 1.0 --slippage-bps 0.5 `
        --signal-variant baseline `
        --threshold-grid "0.44,0.45,0.46,0.47,0.48,0.49,0.50" `
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
Write-Host "===== EURUSD H4 ROLLING WALK-FORWARD SUMMARY (halflife=${WeightHalflifeDays}d) =====" -ForegroundColor Green
Write-Host "Year  Result"
$results | ForEach-Object { Write-Host $_ }
