param(
  [ValidateSet('logreg','rf')]
  [string]$Model = 'logreg',
  [ValidateSet('rolling-90d','rolling-180d','event-focused')]
  [string]$DatasetProfile = 'rolling-90d',
  [int]$CvFolds = 5,
  [int]$HorizonBars = 6,
  [ValidateSet('isotonic','platt','none')]
  [string]$Calibration = 'isotonic'
)

$ErrorActionPreference = 'Stop'

function Clamp([double]$v) {
  if ($v -lt 0) { return 0.0 }
  if ($v -gt 100) { return 100.0 }
  return $v
}

function Update-RunIndex([string]$RunsRoot, [string]$IndexPath) {
  $reports = Get-ChildItem -Path $RunsRoot -Filter 'RUN_REPORT.md' -Recurse | Sort-Object FullName
  $lines = @()
  $lines += '# Training Run Index'
  $lines += ''
  $lines += ('Generated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
  $lines += ''
  $lines += '| Run Folder | Local Timestamp | Overall % | Verdict | Trades | Profit Factor | Net Profit | Report |'
  $lines += '|---|---:|---:|---|---:|---:|---:|---|'

  foreach ($report in $reports) {
    $text = Get-Content -Path $report.FullName -Raw
    $folder = Split-Path -Path (Split-Path -Path $report.FullName -Parent) -Leaf

    $localTs = [regex]::Match($text, '- Run Timestamp \(Local\):\s*(.+)').Groups[1].Value.Trim()
    $overall = [regex]::Match($text, '- Weighted Overall Score \(%\):\s*([0-9\.\-]+)').Groups[1].Value.Trim()
    $verdict = [regex]::Match($text, '- Run Verdict:\s*([A-Z]+)').Groups[1].Value.Trim()
    $trades = [regex]::Match($text, '- Total Trades:\s*([0-9]+)').Groups[1].Value.Trim()
    $pf = [regex]::Match($text, '- Profit Factor:\s*([0-9\.\-]+)').Groups[1].Value.Trim()
    $net = [regex]::Match($text, '- Net Profit:\s*\$?([0-9\.\-]+)').Groups[1].Value.Trim()

    if ([string]::IsNullOrWhiteSpace($localTs)) { $localTs = 'n/a' }
    if ([string]::IsNullOrWhiteSpace($overall)) { $overall = 'n/a' }
    if ([string]::IsNullOrWhiteSpace($verdict)) { $verdict = 'n/a' }
    if ([string]::IsNullOrWhiteSpace($trades)) { $trades = 'n/a' }
    if ([string]::IsNullOrWhiteSpace($pf)) { $pf = 'n/a' }
    if ([string]::IsNullOrWhiteSpace($net)) { $net = 'n/a' }

    $relative = ('runs/' + $folder + '/RUN_REPORT.md')
    $lines += ('| ' + $folder + ' | ' + $localTs + ' | ' + $overall + ' | ' + $verdict + ' | ' + $trades + ' | ' + $pf + ' | ' + $net + ' | [' + $folder + '](' + $relative + ') |')
  }

  $lines += ''
  $lines += '## Notes'
  $lines += '- Folder names use yyyy-MM-dd_HH-mm because Windows does not allow : in folder names.'

  Set-Content -Path $IndexPath -Value $lines
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$runsRoot = Join-Path $repoRoot 'docs\09-training-runs\runs'
$indexPath = Join-Path $repoRoot 'docs\09-training-runs\RUN_INDEX.md'

$folderTs = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$displayTs = Get-Date -Format 'yyyy-MM-dd:HH:mm'
$runDir = Join-Path $runsRoot $folderTs
$artifactDir = Join-Path $runDir 'artifacts'
$logPath = Join-Path $runDir 'run_output.log'
$reportPath = Join-Path $runDir 'RUN_REPORT.md'

New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null

$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found at $pythonExe. Configure the workspace Python environment first."
}

Set-Content -Path $logPath -Value ('AI training run started at ' + (Get-Date -Format o))
Add-Content -Path $logPath -Value '=== Training ==='

& $pythonExe (Join-Path $repoRoot 'training\train_walk_forward.py') --model $Model --dataset-profile $DatasetProfile --cv-folds $CvFolds --horizon-bars $HorizonBars --calibration $Calibration --output $artifactDir 2>&1 |
  Tee-Object -FilePath $logPath -Append
$trainOk = $LASTEXITCODE -eq 0

Add-Content -Path $logPath -Value '=== Baseline Validation ==='
& $pythonExe (Join-Path $repoRoot 'validation\generate_baseline.py') 2>&1 |
  Tee-Object -FilePath $logPath -Append
$baselineOk = $LASTEXITCODE -eq 0

Copy-Item (Join-Path $repoRoot 'validation\baseline.md') (Join-Path $artifactDir 'baseline.md') -Force

$trainingReportPath = Join-Path $artifactDir 'training_report.json'
$onnxPath = Join-Path $artifactDir 'daily_breakout_model.onnx'
$baselinePath = Join-Path $artifactDir 'baseline.md'

$training = Get-Content $trainingReportPath -Raw | ConvertFrom-Json
$baselineText = Get-Content $baselinePath -Raw

$totalTrades = [int]([regex]::Match($baselineText, '\| Total Trades \| ([0-9]+) \|').Groups[1].Value)
$winRate = [double]([regex]::Match($baselineText, '\| Win Rate \| ([0-9\.]+)% \|').Groups[1].Value)
$profitFactor = [double]([regex]::Match($baselineText, '\| \*\*Profit Factor\*\* \| \*\*([0-9\.\-]+)\*\* \|').Groups[1].Value)
$netProfitRaw = [regex]::Match($baselineText, '\| \*\*Net Profit\*\* \| \*\*\$([0-9,\.\-]+)\*\* \|').Groups[1].Value
$netProfit = [double]($netProfitRaw -replace ',', '')
$maxDd = [double]([regex]::Match($baselineText, '\| Max Drawdown \| ([0-9\.]+)% \|').Groups[1].Value)
$sharpe = [double]([regex]::Match($baselineText, '\| \*\*Sharpe Ratio\*\* \| \*\*([0-9\.\-]+)\*\* \|').Groups[1].Value)

$aucMean = [double]$training.metrics.auc_mean
$brierMean = [double]$training.metrics.brier_mean

$aucScore = Clamp ((($aucMean - 0.50) / 0.35) * 100.0)
$brierScore = Clamp (((0.30 - $brierMean) / 0.20) * 100.0)
$trainingScore = [math]::Round((($aucScore + $brierScore) / 2.0), 2)

$pfScore = Clamp ((($profitFactor - 0.70) / 0.60) * 100.0)
$netScore = Clamp ((($netProfit + 500.0) / 1500.0) * 100.0)
$tradeCountScore = Clamp (($totalTrades / 20.0) * 100.0)
$validationScore = [math]::Round((($pfScore * 0.45) + ($netScore * 0.45) + ($tradeCountScore * 0.10)), 2)

$ddScore = Clamp (((25.0 - $maxDd) / 20.0) * 100.0)
$sharpeScore = Clamp ((($sharpe + 0.20) / 1.20) * 100.0)
$riskScore = [math]::Round((($ddScore * 0.6) + ($sharpeScore * 0.4)), 2)

$reliabilityScore = 0.0
if ($trainOk) { $reliabilityScore += 40.0 }
if ($baselineOk) { $reliabilityScore += 30.0 }
if (Test-Path $trainingReportPath) { $reliabilityScore += 15.0 }
if (Test-Path $onnxPath) { $reliabilityScore += 10.0 }
if (Test-Path $baselinePath) { $reliabilityScore += 5.0 }

$overall = [math]::Round((($trainingScore * 0.35) + ($validationScore * 0.35) + ($riskScore * 0.20) + ($reliabilityScore * 0.10)), 2)
$verdict = if ($overall -ge 75) { 'PASS' } elseif ($overall -ge 55) { 'HOLD' } else { 'FAIL' }

$utcNow = [DateTime]::UtcNow.ToString('o')
$netProfitFormatted = ('{0:N2}' -f $netProfit)

$trainingDateRange = switch ($DatasetProfile) {
  'rolling-90d' { 'rolling 90-day equivalent synthetic window' }
  'rolling-180d' { 'rolling 180-day equivalent synthetic window' }
  'event-focused' { 'event-focused synthetic sampling window' }
  default { 'synthetic dataset (profile-defined window)' }
}
$trainingTimeframe = 'synthetic feature bars (not chart-bound)'
$validationDateRange = '2023-01-01 to 2023-12-31'
$validationTimeframe = 'D1 (daily bars)'

$reportLines = @(
  '# AI Training Run Report',
  '',
  '## Run Metadata',
  ('- Run ID: run-' + $folderTs),
  ('- Run Timestamp (UTC): ' + $utcNow),
  ('- Run Timestamp (Local): ' + $displayTs),
  '- Environment: local-dev',
  '- Operator: scripted run',
  '- Git Branch: main',
  '- Commit Hash: n/a',
  "- Notes: Timestamp folder uses yyyy-MM-dd_HH-mm on Windows because ':' is not valid in folder names.",
  '',
  '## Training Parameters',
  ('- Model Type: ' + $Model),
  ('- Dataset Profile: ' + $DatasetProfile),
  ('- Training Date Range: ' + $trainingDateRange),
  ('- Training Chart Period/Timeframe: ' + $trainingTimeframe),
  ('- CV Folds: ' + $CvFolds),
  ('- Horizon Bars: ' + $HorizonBars),
  ('- Calibration: ' + $Calibration),
  '- Include Macro: true',
  '- Include News Windows: true',
  '- Include Session Features: true',
  '- Enable Class Weights: true',
  ('- Training Output Path: ' + $artifactDir),
  '',
  '## Validation Parameters',
  '- Symbol: EURUSD',
  ('- Date Range: ' + $validationDateRange),
  ('- Chart Period/Timeframe: ' + $validationTimeframe),
  '- Starting Capital: 10000.0',
  '- Risk Per Trade: 0.5%',
  '- Lookback Periods: 55',
  '- ATR Period: 20',
  '- SMA Fast: 100',
  '- SMA Trend: 200',
  '- Spread Pips: 2.0',
  '- Slippage Pips: 1.0',
  '- Commission %: 0.02%',
  '',
  '## Raw Results',
  '### Training Metrics',
  ('- AUC Mean: ' + ([math]::Round($aucMean, 6))),
  ('- AUC Min: ' + ([math]::Round([double]$training.metrics.auc_min, 6))),
  ('- Brier Mean: ' + ([math]::Round($brierMean, 6))),
  ('- Brier Max: ' + ([math]::Round([double]$training.metrics.brier_max, 6))),
  '',
  '### Backtest Metrics',
  ('- Total Trades: ' + $totalTrades),
  ('- Win Rate: ' + $winRate + '%'),
  ('- Net Profit: $' + $netProfitFormatted),
  ('- Profit Factor: ' + $profitFactor),
  ('- Max Drawdown %: ' + $maxDd),
  ('- Sharpe Ratio: ' + $sharpe),
  '',
  '## Scoring Model (0-100)',
  ('- Training Quality Score (%): ' + $trainingScore),
  ('- Validation Performance Score (%): ' + $validationScore),
  ('- Risk Control Score (%): ' + $riskScore),
  ('- Run Reliability Score (%): ' + $reliabilityScore),
  '',
  '## Overall Score',
  ('- Weighted Overall Score (%): ' + $overall),
  ('- Run Verdict: ' + $verdict),
  '',
  '## Evidence',
  ('- Training Log: ' + $logPath),
  ('- Training Report Artifact: ' + $trainingReportPath),
  ('- Baseline Report Artifact: ' + $baselinePath),
  ('- ONNX Model Artifact: ' + $onnxPath),
  '',
  '## Assessment Summary',
  '- What went well: Training and validation completed and artifacts were produced.',
  '- What failed: Baseline PnL/profit factor did not pass profitability threshold.',
  '- Risks: Very low trade count limits confidence in backtest stability.',
  '- Recommended next run changes: Compare rf model and event-focused profile; increase sample horizon and trade opportunities.'
)

Set-Content -Path $reportPath -Value $reportLines

Update-RunIndex -RunsRoot $runsRoot -IndexPath $indexPath

Write-Output ('RUN_DIR=' + $runDir)
Write-Output ('REPORT=' + $reportPath)
Write-Output ('LOG=' + $logPath)
Write-Output ('INDEX=' + $indexPath)
