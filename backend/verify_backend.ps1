function Test-Endpoint {
    param($Method, $Path, $Body = $null)
    $url = "http://127.0.0.1:3000$Path"
    try {
        if ($Method -eq "POST") {
            $response = Invoke-WebRequest -Uri $url -Method Post -Body ($Body | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
        } else {
            $response = Invoke-WebRequest -Uri $url -Method Get -ErrorAction Stop
        }
        $data = $response.Content | ConvertFrom-Json
        $summary = "ok"
        if ($data.status) { $summary = $data.status }
        elseif ($data.count -ne $null) { $summary = "count: $($data.count)" }
        elseif ($data.items -ne $null) { $summary = "count: $($data.items.Count)" }
        elseif ($data.strategyId) { $summary = "strategy: $($data.strategyId)" }
        
        return [PSCustomObject]@{ Method = $Method; Path = $Path; Status = $response.StatusCode; Summary = $summary }
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        $errorMsg = if ($_.Exception.Response) { ($_.Exception.Response.GetResponseStream() | New-Object System.IO.StreamReader).ReadToEnd() } else { $_.Exception.Message }
        try { 
            $errData = $errorMsg | ConvertFrom-Json
            if ($errData.error.code) { $summary = "err: $($errData.error.code)" } else { $summary = "err" }
        } catch { $summary = "err: $status" }
        return [PSCustomObject]@{ Method = $Method; Path = $Path; Status = $status; Summary = $summary }
    }
}

function Test-Fmp($Path, $Name, $UseHeader = $false) {
    $apiKey = (Get-Content .env | Select-String "FMP_API_KEY=").ToString().Split("=")[1].Trim()
    $baseUrl = "https://financialmodelingprep.com"
    $url = "$baseUrl$Path"
    if (-not $UseHeader) {
        $sep = if ($url.Contains("?")) { "&" } else { "?" }
        $url += "$($sep)apikey=$apiKey"
    }
    
    try {
        $headers = if ($UseHeader) { @{ "apikey" = $apiKey } } else { @{} }
        $response = Invoke-WebRequest -Uri $url -Headers $headers -Method Get -ErrorAction Stop
        $data = $response.Content | ConvertFrom-Json
        $count = if ($data.Count -ne $null) { $data.Count } else { "N/A" }
        return [PSCustomObject]@{ API = "FMP ($Name)"; Status = $response.StatusCode; Items = $count }
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        return [PSCustomObject]@{ API = "FMP ($Name)"; Status = $status; Items = "Error" }
    }
}

Write-Host "--- 1) Building ---"
npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }

Write-Host "--- 2) Starting Backend ---"
$proc = Start-Process node -ArgumentList "dist/index.js" -PassThru -NoNewWindow
$start = Get-Date
$timeoutSeconds = 30
$running = $false

Write-Host "--- 3) Waiting for health check ---"
while ((Get-Date) -lt $start.AddSeconds($timeoutSeconds)) {
   try {
       $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000/health" -Method Get -ErrorAction SilentlyContinue
       if ($resp.StatusCode -eq 200) { $running = $true; break }
   } catch { }
   Start-Sleep -Seconds 1
}

if (-not $running) {
    Write-Error "Backend failed to start"
    Stop-Process -Id $proc.Id -Force
    exit 1
}

Write-Host "--- 4) Testing Backend Routes ---"
$results = @()
$results += Test-Endpoint "GET" "/health"
$results += Test-Endpoint "GET" "/news/providers"
$results += Test-Endpoint "GET" "/news/active?limit=5"
$results += Test-Endpoint "GET" "/news/upcoming?limit=5"
$results += Test-Endpoint "POST" "/trades/open" -Body @{ symbol = "AAPL"; side = "buy"; quantity = 1 }
$results += Test-Endpoint "GET" "/trades/open"
$results += Test-Endpoint "GET" "/model-version"
$results += Test-Endpoint "GET" "/performance"
$results += Test-Endpoint "POST" "/log-signal" -Body @{ signalId = "test"; action = "buy" }
$results += Test-Endpoint "POST" "/log-rejected-signal" -Body @{ reason = "risk" }
$results += Test-Endpoint "POST" "/log-trade" -Body @{ tradeId = "test" }
$results += Test-Endpoint "POST" "/risk-check" -Body @{ symbol = "AAPL"; side = "buy" }
$results += Test-Endpoint "POST" "/portfolio/evaluate" -Body @{ symbols = @("AAPL") }
$results += Test-Endpoint "POST" "/signal" -Body @{ ticker = "AAPL"; action = "BUY" }

Write-Host "--- 5) Testing FMP APIs ---"
$fmpResults = @()
$fmpResults += Test-Fmp "/api/v3/economic_calendar" "V3 Current"
$fmpResults += Test-Fmp "/api/v3/economic_calendar?from=2024-01-01&to=2024-01-31" "V3 Hist"
$fmpResults += Test-Fmp "/stable/economic-calendar" "Stable Current (H)" -UseHeader $true
$fmpResults += Test-Fmp "/stable/economic-calendar?from=2024-01-01&to=2024-01-31" "Stable Hist (H)" -UseHeader $true
$fmpResults += Test-Fmp "/stable/economic-calendar?from=2024-01-01&to=2024-01-31" "Stable Hist Fallback (Q)"

Write-Host "`nBackend API Results:"
$results | Format-Table -AutoSize
Write-Host "`nExternal FMP API Results:"
$fmpResults | Format-Table -AutoSize

Write-Host "--- 6) Stopping Backend ---"
Stop-Process -Id $proc.Id -Force
