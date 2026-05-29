param(
  [Parameter(Mandatory = $true)]
  [string]$ReportPath,
  [double]$MaxDrawdownPct = -15.0,
  [int]$MinTrades = 120,
  [double]$MinProfitFactor = 1.05,
  [double]$MinNetReturnPct = 0.0,
  [double]$MinStressNetReturnPct = 0.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ReportPath)) {
  throw "Report not found: $ReportPath"
}

$report = Get-Content $ReportPath -Raw | ConvertFrom-Json

$strategy = $report.strategyBacktest
$stress = $report.strategyBacktestStressCost
$wf = $report.walkForwardSelection

$dataLineagePass = (
  [int]$report.bars.trainFetched -gt 0 -and
  [int]$report.bars.testFetched -gt 0 -and
  [int]$wf.foldsUsed -ge 2 -and
  [string]::IsNullOrWhiteSpace([string]$report.modelPath) -eq $false
)

$statPass = (
  [bool]$wf.constraintsSatisfied -eq $true -and
  [string]$wf.selectionMode -eq 'constrained'
)

$riskPass = (
  [int]$strategy.totalTrades -ge $MinTrades -and
  [double]$strategy.profitFactor -ge $MinProfitFactor -and
  [double]$strategy.maxDrawdownPct -ge $MaxDrawdownPct -and
  [double]$strategy.netReturnPct -ge $MinNetReturnPct -and
  [double]$stress.netReturnPct -ge $MinStressNetReturnPct
)

$operationalPass = $false
$liveReadinessPass = $false

$decision = 'REJECT'
if ($dataLineagePass -and $statPass -and $riskPass) {
  $decision = 'PAPER_ONLY'
}
if ($dataLineagePass -and $statPass -and $riskPass -and $operationalPass) {
  $decision = 'MICRO_LIVE'
}
if ($dataLineagePass -and $statPass -and $riskPass -and $operationalPass -and $liveReadinessPass) {
  $decision = 'PROMOTE'
}

$result = [PSCustomObject]@{
  generatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
  reportPath = (Resolve-Path $ReportPath).Path
  thresholds = [PSCustomObject]@{
    maxDrawdownPct = $MaxDrawdownPct
    minTrades = $MinTrades
    minProfitFactor = $MinProfitFactor
    minNetReturnPct = $MinNetReturnPct
    minStressNetReturnPct = $MinStressNetReturnPct
  }
  gates = [PSCustomObject]@{
    dataAndLineage = [PSCustomObject]@{
      pass = $dataLineagePass
      details = [PSCustomObject]@{
        trainFetched = [int]$report.bars.trainFetched
        testFetched = [int]$report.bars.testFetched
        foldsUsed = [int]$wf.foldsUsed
        modelPath = [string]$report.modelPath
      }
    }
    statisticalRobustness = [PSCustomObject]@{
      pass = $statPass
      details = [PSCustomObject]@{
        constraintsSatisfied = [bool]$wf.constraintsSatisfied
        selectionMode = [string]$wf.selectionMode
      }
    }
    tradingRisk = [PSCustomObject]@{
      pass = $riskPass
      details = [PSCustomObject]@{
        totalTrades = [int]$strategy.totalTrades
        profitFactor = [double]$strategy.profitFactor
        maxDrawdownPct = [double]$strategy.maxDrawdownPct
        netReturnPct = [double]$strategy.netReturnPct
        stressNetReturnPct = [double]$stress.netReturnPct
      }
    }
    operationalReliability = [PSCustomObject]@{
      pass = $operationalPass
      details = 'Not evaluated in this script; fail-closed.'
    }
    liveReadiness = [PSCustomObject]@{
      pass = $liveReadinessPass
      details = 'Not evaluated in this script; fail-closed.'
    }
  }
  decision = $decision
}

$outPath = Join-Path (Split-Path $ReportPath -Parent) 'ts003_gate_evaluation.json'
$result | ConvertTo-Json -Depth 8 | Set-Content -Path $outPath -Encoding UTF8
Write-Output "GATE_EVALUATION=$outPath"
Write-Output "DECISION=$decision"
