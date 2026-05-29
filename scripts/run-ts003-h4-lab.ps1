param(
  [switch]$AllowFallbackSelection
)

Set-Location c:\moschops_01
$ErrorActionPreference = 'Stop'

$rootTs = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$labDir = "c:\moschops_01\docs\09-training-runs\runs\$rootTs-ts003-h4-lab"
New-Item -ItemType Directory -Path $labDir -Force | Out-Null

$python = 'c:/moschops_01/.venv/Scripts/python.exe'
$script = 'c:/moschops_01/training/run_historical_split.py'
$gateEvalScript = 'c:/moschops_01/scripts/evaluate-ts003-gates.ps1'
$targetMaxDd = -15.0
$targetMinMedianTrades = 120
$fallbackMinMedianTrades = 5
$enableRegimeGate = $true
$regimeMinTrendStrength = 0.0
$regimeMaxVolatilityRegime = 1.8
$labelMode = 'edge'
$minEdgeBps = 8.0

$variants = @(
  @{
    name='trend-follow';
    trendMinStrength=0.0002;
    trendMinBreakoutDistance=0.0000;
    splitTrendStrength=0.0008;
    mrMaxBreakoutDistance=-0.0010;
    mrMaxRet10=0.0;
    mrMaxVolatilityRegime=1.3;
    mrThresholdOffset=-0.05
  },
  @{
    name='regime-split';
    trendMinStrength=0.0002;
    trendMinBreakoutDistance=0.0000;
    splitTrendStrength=0.0008;
    mrMaxBreakoutDistance=-0.0015;
    mrMaxRet10=-0.0010;
    mrMaxVolatilityRegime=1.2;
    mrThresholdOffset=-0.08
  }
)

# Development sweep window: 8y train, 2y forward for config selection.
$devTrainStart = '2014-05-28'
$devTrainEnd = '2022-05-27'
$devTestStart = '2022-05-28'
$devTestEnd = '2024-05-27'

# Locked holdout acceptance window: 10y train, last 2y forward.
$holdoutTrainStart = '2014-05-28'
$holdoutTrainEnd = '2024-05-27'
$holdoutTestStart = '2024-05-28'
$holdoutTestEnd = '2026-05-27'

$configs = @(
  @{id='R01'; horizon=3; wf=5; emb=5; grid='0.45,0.50,0.55,0.60'},
  @{id='R02'; horizon=6; wf=5; emb=5; grid='0.45,0.50,0.55,0.60'},
  @{id='R03'; horizon=12; wf=5; emb=5; grid='0.40,0.45,0.50,0.55'},
  @{id='R04'; horizon=6; wf=6; emb=5; grid='0.40,0.45,0.50,0.55'},
  @{id='R05'; horizon=6; wf=6; emb=10; grid='0.45,0.50,0.55,0.60'},
  @{id='R06'; horizon=12; wf=6; emb=10; grid='0.40,0.45,0.50,0.55'},
  @{id='R07'; horizon=18; wf=5; emb=10; grid='0.40,0.45,0.50,0.55'},
  @{id='R08'; horizon=24; wf=5; emb=10; grid='0.35,0.40,0.45,0.50'},
  @{id='R09'; horizon=9; wf=7; emb=10; grid='0.45,0.50,0.55,0.60'}
)

$summary = @()

foreach($variant in $variants){
  foreach($cfg in $configs){
    $runDir = Join-Path $labDir ("{0}-{1}-dev" -f $variant.name, $cfg.id)
    $artifactDir = Join-Path $runDir 'artifacts'
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

    $devArgs = @(
      '--train-start', $devTrainStart,
      '--train-end', $devTrainEnd,
      '--test-start', $devTestStart,
      '--test-end', $devTestEnd,
      '--timeframe', 'H4',
      '--symbol', 'EURUSD',
      '--source', 'FMP',
      '--horizon-bars', $cfg.horizon,
      '--walk-forward-folds', $cfg.wf,
      '--embargo-bars', $cfg.emb,
      '--spread-bps', '2.0',
      '--slippage-bps', '1.0',
      '--commission-bps', '0.5',
      '--stress-cost-multiplier', '2.0',
      '--threshold-grid', $cfg.grid,
      '--target-max-drawdown-pct', $targetMaxDd,
      '--target-min-median-trades', $targetMinMedianTrades,
      '--fallback-min-median-trades', $fallbackMinMedianTrades,
      '--regime-min-trend-strength', $regimeMinTrendStrength,
      '--regime-max-volatility-regime', $regimeMaxVolatilityRegime,
      '--label-mode', $labelMode,
      '--min-edge-bps', $minEdgeBps,
      '--signal-variant', $variant.name,
      '--trend-min-strength', $variant.trendMinStrength,
      '--trend-min-breakout-distance', $variant.trendMinBreakoutDistance,
      '--split-trend-strength', $variant.splitTrendStrength,
      '--mr-max-breakout-distance', $variant.mrMaxBreakoutDistance,
      '--mr-max-ret10', $variant.mrMaxRet10,
      '--mr-max-volatility-regime', $variant.mrMaxVolatilityRegime,
      '--mr-threshold-offset', $variant.mrThresholdOffset,
      '--output-dir', $artifactDir
    )
    if($enableRegimeGate){
      $devArgs += '--enable-regime-gate'
    }

    & $python $script @devArgs | Tee-Object -FilePath (Join-Path $runDir 'run_output.log') | Out-Null

    $jsonPath = Join-Path $artifactDir 'historical_split_report.json'
    if (-not (Test-Path $jsonPath)) {
      $lastLine = ''
      $logPath = Join-Path $runDir 'run_output.log'
      if (Test-Path $logPath) {
        $lastLine = (Get-Content $logPath | Select-Object -Last 1)
      }

      $summary += [PSCustomObject]@{
        runId=$cfg.id
        variant=$variant.name
        kind='dev'
        runDir=$runDir
        horizon=$cfg.horizon
        folds=$cfg.wf
        embargo=$cfg.emb
        grid=$cfg.grid
        selectedThreshold=0.0
        selectionMode='runtime-error'
        constraintsSatisfied=$false
        gateDecision='REJECT'
        gateDataPass=$false
        gateStatPass=$false
        gateRiskPass=$false
        trades=0
        netReturnPct=0.0
        profitFactor=0.0
        maxDrawdownPct=0.0
        stressNetReturnPct=0.0
        stressProfitFactor=0.0
        score=-999999.0
        error=$lastLine
      }
      continue
    }

    $r = Get-Content $jsonPath -Raw | ConvertFrom-Json
    & $gateEvalScript -ReportPath $jsonPath | Out-Null
    $gatePath = Join-Path $artifactDir 'ts003_gate_evaluation.json'
    $gate = Get-Content $gatePath -Raw | ConvertFrom-Json

  $pf = [double]$r.strategyBacktest.profitFactor
  $dd = [double]$r.strategyBacktest.maxDrawdownPct
  $net = [double]$r.strategyBacktest.netReturnPct
  $trades = [double]$r.strategyBacktest.totalTrades
  $stressPf = [double]$r.strategyBacktestStressCost.profitFactor
  $stressNet = [double]$r.strategyBacktestStressCost.netReturnPct

  # Cap PF contribution to avoid tiny-trade PF spikes dominating the ranking.
  $pfCap = [math]::Min($pf, 5.0)
  $stressPfCap = [math]::Min($stressPf, 5.0)

  $score = ($net * 1.0) + ($pfCap * 6.0) + ($stressPfCap * 5.0) + ($stressNet * 0.7) + ($dd * 0.9)
  if($trades -lt $targetMinMedianTrades){ $score -= 25.0 }
  if($dd -lt $targetMaxDd){ $score -= 25.0 }

    $summary += [PSCustomObject]@{
      runId=$cfg.id
      variant=$variant.name
      kind='dev'
      runDir=$runDir
      horizon=$cfg.horizon
      folds=$cfg.wf
      embargo=$cfg.emb
      grid=$cfg.grid
      selectedThreshold=[double]$r.metrics.selectedThreshold
      selectionMode=$r.walkForwardSelection.selectionMode
      constraintsSatisfied=[bool]$r.walkForwardSelection.constraintsSatisfied
      gateDecision=[string]$gate.decision
      gateDataPass=[bool]$gate.gates.dataAndLineage.pass
      gateStatPass=[bool]$gate.gates.statisticalRobustness.pass
      gateRiskPass=[bool]$gate.gates.tradingRisk.pass
      trades=[int]$trades
      netReturnPct=[math]::Round($net,4)
      profitFactor=[math]::Round($pf,4)
      maxDrawdownPct=[math]::Round($dd,4)
      stressNetReturnPct=[math]::Round($stressNet,4)
      stressProfitFactor=[math]::Round($stressPf,4)
      score=[math]::Round($score,4)
    }
  }
}

$devSummary = $summary | Where-Object { $_.kind -eq 'dev' }
$feasibleDevSummary = $devSummary | Where-Object { $_.constraintsSatisfied -eq $true }

$summaryPath = Join-Path $labDir 'summary.json'
$csvPath = Join-Path $labDir 'summary.csv'

if (-not $AllowFallbackSelection -and (-not $feasibleDevSummary -or $feasibleDevSummary.Count -eq 0)) {
  $summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
  $summary | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

  $variantDiagnostics = @()
  foreach($v in ($devSummary | Group-Object variant)){
    $rows = $v.Group
    $maxTrades = [int](($rows | Measure-Object -Property trades -Maximum).Maximum)
    $bestDd = [double](($rows | Measure-Object -Property maxDrawdownPct -Maximum).Maximum)
    $bestNet = [double](($rows | Measure-Object -Property netReturnPct -Maximum).Maximum)
    $variantDiagnostics += [PSCustomObject]@{
      variant = [string]$v.Name
      maxTradesObserved = $maxTrades
      tradeCountShortfallVsTarget = [int]($targetMinMedianTrades - $maxTrades)
      bestObservedMaxDrawdownPct = [math]::Round($bestDd,4)
      bestObservedNetReturnPct = [math]::Round($bestNet,4)
    }
  }

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
    feasibilityGapDiagnostics = $variantDiagnostics
    nextAction = 'Revise feature/risk setup and rerun; do not tune on holdout.'
  }

  $blockerPath = Join-Path $labDir 'selection_blocker.json'
  $blocker | ConvertTo-Json -Depth 6 | Set-Content -Path $blockerPath -Encoding UTF8

  Write-Output "LAB_DIR=$labDir"
  Write-Output "SUMMARY_JSON=$summaryPath"
  Write-Output "SUMMARY_CSV=$csvPath"
  Write-Output "SELECTION_BLOCKER=$blockerPath"
  throw 'No feasible TS-003 development configuration under hard constraints. Holdout run blocked by policy.'
}

$candidatePool = if ($feasibleDevSummary -and $feasibleDevSummary.Count -gt 0) { $feasibleDevSummary } else { $devSummary }
$best = $candidatePool | Sort-Object score -Descending | Select-Object -First 1
if (-not $best) {
  throw 'No valid TS-003 development runs were captured; cannot select holdout config.'
}

$holdoutDir = Join-Path $labDir ("{0}-R10-holdout-final" -f $best.variant)
$holdoutArtifact = Join-Path $holdoutDir 'artifacts'
New-Item -ItemType Directory -Path $holdoutArtifact -Force | Out-Null

$holdoutArgs = @(
  '--train-start', $holdoutTrainStart,
  '--train-end', $holdoutTrainEnd,
  '--test-start', $holdoutTestStart,
  '--test-end', $holdoutTestEnd,
  '--timeframe', 'H4',
  '--symbol', 'EURUSD',
  '--source', 'FMP',
  '--horizon-bars', $best.horizon,
  '--walk-forward-folds', $best.folds,
  '--embargo-bars', $best.embargo,
  '--spread-bps', '2.0',
  '--slippage-bps', '1.0',
  '--commission-bps', '0.5',
  '--stress-cost-multiplier', '2.0',
  '--threshold-grid', $best.grid,
  '--target-max-drawdown-pct', $targetMaxDd,
  '--target-min-median-trades', $targetMinMedianTrades,
  '--fallback-min-median-trades', $fallbackMinMedianTrades,
  '--regime-min-trend-strength', $regimeMinTrendStrength,
  '--regime-max-volatility-regime', $regimeMaxVolatilityRegime,
  '--label-mode', $labelMode,
  '--min-edge-bps', $minEdgeBps,
  '--signal-variant', $best.variant,
  '--trend-min-strength', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).trendMinStrength),
  '--trend-min-breakout-distance', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).trendMinBreakoutDistance),
  '--split-trend-strength', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).splitTrendStrength),
  '--mr-max-breakout-distance', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).mrMaxBreakoutDistance),
  '--mr-max-ret10', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).mrMaxRet10),
  '--mr-max-volatility-regime', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).mrMaxVolatilityRegime),
  '--mr-threshold-offset', (($variants | Where-Object { $_.name -eq $best.variant } | Select-Object -First 1).mrThresholdOffset),
  '--output-dir', $holdoutArtifact
)
if($enableRegimeGate){
  $holdoutArgs += '--enable-regime-gate'
}

& $python $script @holdoutArgs | Tee-Object -FilePath (Join-Path $holdoutDir 'run_output.log') | Out-Null

$hrPath = Join-Path $holdoutArtifact 'historical_split_report.json'
$hr = Get-Content $hrPath -Raw | ConvertFrom-Json
& $gateEvalScript -ReportPath $hrPath | Out-Null
$hGatePath = Join-Path $holdoutArtifact 'ts003_gate_evaluation.json'
$hGate = Get-Content $hGatePath -Raw | ConvertFrom-Json
$summary += [PSCustomObject]@{
  runId='R10'
  variant=[string]$best.variant
  kind='holdout'
  runDir=$holdoutDir
  horizon=$best.horizon
  folds=$best.folds
  embargo=$best.embargo
  grid=$best.grid
  selectedThreshold=[double]$hr.metrics.selectedThreshold
  selectionMode=$hr.walkForwardSelection.selectionMode
  constraintsSatisfied=[bool]$hr.walkForwardSelection.constraintsSatisfied
  gateDecision=[string]$hGate.decision
  gateDataPass=[bool]$hGate.gates.dataAndLineage.pass
  gateStatPass=[bool]$hGate.gates.statisticalRobustness.pass
  gateRiskPass=[bool]$hGate.gates.tradingRisk.pass
  trades=[int]$hr.strategyBacktest.totalTrades
  netReturnPct=[math]::Round([double]$hr.strategyBacktest.netReturnPct,4)
  profitFactor=[math]::Round([double]$hr.strategyBacktest.profitFactor,4)
  maxDrawdownPct=[math]::Round([double]$hr.strategyBacktest.maxDrawdownPct,4)
  stressNetReturnPct=[math]::Round([double]$hr.strategyBacktestStressCost.netReturnPct,4)
  stressProfitFactor=[math]::Round([double]$hr.strategyBacktestStressCost.profitFactor,4)
  score=[math]::Round(([double]$hr.strategyBacktest.netReturnPct + ([math]::Min([double]$hr.strategyBacktest.profitFactor,5.0) * 6.0)),4)
}

$summary | ConvertTo-Json -Depth 6 | Set-Content -Path $summaryPath -Encoding UTF8
$summary | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8

Write-Output "LAB_DIR=$labDir"
Write-Output "BEST_DEV_RUN=$($best.runId)"
Write-Output "BEST_CONFIG=H$($best.horizon)-F$($best.folds)-E$($best.embargo)-G$($best.grid)"
Write-Output "SUMMARY_JSON=$summaryPath"
Write-Output "SUMMARY_CSV=$csvPath"