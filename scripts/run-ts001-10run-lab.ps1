param(
  [switch]$AllowFallbackSelection
)

Set-Location c:\moschops_01
$ErrorActionPreference = 'Stop'

$rootTs = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$labDir = "c:\moschops_01\docs\09-training-runs\runs\$rootTs-ts001-10run-lab"
New-Item -ItemType Directory -Path $labDir -Force | Out-Null

$python = 'c:/moschops_01/.venv/Scripts/python.exe'
$script = 'c:/moschops_01/training/run_historical_split.py'
$targetMaxDd = -15.0
$targetMinMedianTrades = 80

$configs = @(
  @{id='R01'; horizon=5; wf=5; emb=5; grid='0.45,0.50,0.55,0.60'},
  @{id='R02'; horizon=5; wf=6; emb=5; grid='0.40,0.45,0.50,0.55'},
  @{id='R03'; horizon=5; wf=5; emb=10; grid='0.45,0.50,0.55,0.60'},
  @{id='R04'; horizon=3; wf=5; emb=5; grid='0.45,0.50,0.55,0.60'},
  @{id='R05'; horizon=7; wf=5; emb=5; grid='0.40,0.45,0.50,0.55'},
  @{id='R06'; horizon=10; wf=5; emb=5; grid='0.40,0.45,0.50,0.55'},
  @{id='R07'; horizon=5; wf=7; emb=10; grid='0.50,0.55,0.60,0.65'},
  @{id='R08'; horizon=7; wf=6; emb=10; grid='0.45,0.50,0.55,0.60'},
  @{id='R09'; horizon=3; wf=6; emb=10; grid='0.50,0.55,0.60,0.65'}
)

$summary = @()

foreach($cfg in $configs){
  $runDir = Join-Path $labDir ("{0}-dev" -f $cfg.id)
  $artifactDir = Join-Path $runDir 'artifacts'
  New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

  & $python $script --train-start 2012-05-28 --train-end 2022-05-27 --test-start 2022-05-28 --test-end 2024-05-27 --timeframe D1 --symbol EURUSD --source FMP --horizon-bars $cfg.horizon --walk-forward-folds $cfg.wf --embargo-bars $cfg.emb --spread-bps 2.0 --slippage-bps 1.0 --commission-bps 0.5 --stress-cost-multiplier 2.0 --threshold-grid $cfg.grid --target-max-drawdown-pct $targetMaxDd --target-min-median-trades $targetMinMedianTrades --output-dir $artifactDir | Tee-Object -FilePath (Join-Path $runDir 'run_output.log') | Out-Null

  $jsonPath = Join-Path $artifactDir 'historical_split_report.json'
  $r = Get-Content $jsonPath -Raw | ConvertFrom-Json

  $pf = [double]$r.strategyBacktest.profitFactor
  $dd = [double]$r.strategyBacktest.maxDrawdownPct
  $net = [double]$r.strategyBacktest.netReturnPct
  $trades = [double]$r.strategyBacktest.totalTrades
  $stressPf = [double]$r.strategyBacktestStressCost.profitFactor
  $stressNet = [double]$r.strategyBacktestStressCost.netReturnPct

  $score = $net + ($pf * 8.0) + ($stressPf * 6.0) + ($stressNet * 0.5) + ($dd * 0.8)
  if($trades -lt 80){ $score -= 20.0 }
  if($dd -lt -25.0){ $score -= 20.0 }

  $summary += [PSCustomObject]@{
    runId=$cfg.id
    kind='dev'
    runDir=$runDir
    horizon=$cfg.horizon
    folds=$cfg.wf
    embargo=$cfg.emb
    grid=$cfg.grid
    selectedThreshold=[double]$r.metrics.selectedThreshold
    selectionMode=$r.walkForwardSelection.selectionMode
    constraintsSatisfied=[bool]$r.walkForwardSelection.constraintsSatisfied
    trades=[int]$trades
    netReturnPct=[math]::Round($net,4)
    profitFactor=[math]::Round($pf,4)
    maxDrawdownPct=[math]::Round($dd,4)
    stressNetReturnPct=[math]::Round($stressNet,4)
    stressProfitFactor=[math]::Round($stressPf,4)
    score=[math]::Round($score,4)
  }
}

$devSummary = $summary | Where-Object { $_.kind -eq 'dev' }
$feasibleDevSummary = $devSummary | Where-Object { $_.constraintsSatisfied -eq $true }

$summaryPath = Join-Path $labDir 'summary.json'
$csvPath = Join-Path $labDir 'summary.csv'

if (-not $AllowFallbackSelection -and (-not $feasibleDevSummary -or $feasibleDevSummary.Count -eq 0)) {
  $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
  $summary | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

  $blocker = [PSCustomObject]@{
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    reason = 'No development run satisfied hard feasibility constraints; holdout run was blocked.'
    feasibilityRules = [PSCustomObject]@{
      targetMaxDrawdownPct = $targetMaxDd
      targetMinMedianTrades = $targetMinMedianTrades
    }
    allowFallbackSelection = [bool]$AllowFallbackSelection
    devRunsEvaluated = [int]($devSummary | Measure-Object).Count
    feasibleDevRuns = 0
    nextAction = 'Revise strategy/risk design and rerun; do not tune on holdout.'
  }

  $blockerPath = Join-Path $labDir 'selection_blocker.json'
  $blocker | ConvertTo-Json -Depth 6 | Set-Content -Path $blockerPath -Encoding UTF8

  Write-Output "LAB_DIR=$labDir"
  Write-Output "SUMMARY_JSON=$summaryPath"
  Write-Output "SUMMARY_CSV=$csvPath"
  Write-Output "SELECTION_BLOCKER=$blockerPath"
  throw 'No feasible development configuration under hard constraints. Holdout run blocked by policy.'
}

$candidatePool = if ($feasibleDevSummary -and $feasibleDevSummary.Count -gt 0) { $feasibleDevSummary } else { $devSummary }
$best = $candidatePool | Sort-Object score -Descending | Select-Object -First 1
if (-not $best) {
  throw 'No valid development runs were captured; cannot select holdout config.'
}

$holdoutDir = Join-Path $labDir 'R10-holdout-final'
$holdoutArtifact = Join-Path $holdoutDir 'artifacts'
New-Item -ItemType Directory -Path $holdoutArtifact -Force | Out-Null

& $python $script --train-start 2014-05-27 --train-end 2024-05-27 --test-start 2024-05-28 --test-end 2026-05-27 --timeframe D1 --symbol EURUSD --source FMP --horizon-bars $best.horizon --walk-forward-folds $best.folds --embargo-bars $best.embargo --spread-bps 2.0 --slippage-bps 1.0 --commission-bps 0.5 --stress-cost-multiplier 2.0 --threshold-grid $best.grid --target-max-drawdown-pct $targetMaxDd --target-min-median-trades $targetMinMedianTrades --output-dir $holdoutArtifact | Tee-Object -FilePath (Join-Path $holdoutDir 'run_output.log') | Out-Null

$hrPath = Join-Path $holdoutArtifact 'historical_split_report.json'
$hr = Get-Content $hrPath -Raw | ConvertFrom-Json
$summary += [PSCustomObject]@{
  runId='R10'
  kind='holdout'
  runDir=$holdoutDir
  horizon=$best.horizon
  folds=$best.folds
  embargo=$best.embargo
  grid=$best.grid
  selectedThreshold=[double]$hr.metrics.selectedThreshold
  selectionMode=$hr.walkForwardSelection.selectionMode
  constraintsSatisfied=[bool]$hr.walkForwardSelection.constraintsSatisfied
  trades=[int]$hr.strategyBacktest.totalTrades
  netReturnPct=[math]::Round([double]$hr.strategyBacktest.netReturnPct,4)
  profitFactor=[math]::Round([double]$hr.strategyBacktest.profitFactor,4)
  maxDrawdownPct=[math]::Round([double]$hr.strategyBacktest.maxDrawdownPct,4)
  stressNetReturnPct=[math]::Round([double]$hr.strategyBacktestStressCost.netReturnPct,4)
  stressProfitFactor=[math]::Round([double]$hr.strategyBacktestStressCost.profitFactor,4)
  score=[math]::Round(([double]$hr.strategyBacktest.netReturnPct + ([double]$hr.strategyBacktest.profitFactor * 8.0)),4)
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

Write-Output "LAB_DIR=$labDir"
Write-Output "BEST_DEV_RUN=$($best.runId)"
Write-Output "BEST_CONFIG=H$($best.horizon)-F$($best.folds)-E$($best.embargo)-G$($best.grid)"
Write-Output "SUMMARY_JSON=$summaryPath"
Write-Output "SUMMARY_CSV=$csvPath"
