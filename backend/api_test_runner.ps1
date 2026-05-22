$ErrorActionPreference = "Stop"
$results = @()
$port = 3000
$baseUrl = "http://localhost:$port"

function Test-Endpoint {
    param($name, $method, $path, $body = $null)
    $url = "$baseUrl$path"
    try {
        $params = @{
            Uri = $url
            Method = $method
            UseBasicParsing = $true
            ContentType = "application/json"
        }
        if ($body) { $params.Body = $body | ConvertTo-Json -Depth 10 }
        
        $resp = Invoke-WebRequest @params
        $ok = $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300
        $summary = if ($resp.Content.Length -gt 50) { $resp.Content.Substring(0, 50) + "..." } else { $resp.Content }
        $res = [PSCustomObject]@{
            name = $name
            statusCode = $resp.StatusCode
            ok = $ok
            summary = $summary.Replace("`n", " ").Replace("`r", "")
        }
    } catch {
        $res = [PSCustomObject]@{
            name = $name
            statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.Value__ } else { 0 }
            ok = $false
            summary = $_.Exception.Message
        }
    }
    $results += $res
    return $res
}

function Test-External {
    param($name, $url, $headers = @{})
    try {
        $resp = Invoke-WebRequest -Uri $url -Headers $headers -Method Get -UseBasicParsing
        $data = $resp.Content | ConvertFrom-Json
        $count = if ($data -is [array]) { $data.Count } elseif ($data.PSObject.Properties.Value -is [array]) { $data.PSObject.Properties.Value.Count } else { 0 }
        $res = [PSCustomObject]@{
            name = $name
            statusCode = $resp.StatusCode
            itemCount = $count
        }
    } catch {
        $res = [PSCustomObject]@{
            name = $name
            statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.Value__ } else { 0 }
            itemCount = 0
        }
    }
    $results += $res
    return $res
}

# 1. Build
Write-Host "Building..."
npm run build

# 2. Start Backend
Write-Host "Starting Backend..."
$logFile = "backend_test_logs.txt"
$process = Start-Process node -ArgumentList "dist/src/index.js" -RedirectStandardOutput $logFile -PassThru -NoNewWindow
$jobId = $process.Id

try {
    # 3. Wait for /health
    Write-Host "Waiting for /health..."
    $timeout = 45
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        try {
            $h = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($h.StatusCode -eq 200) { break }
        } catch {}
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    
    if ($elapsed -ge $timeout) { throw "Backend failed to start" }

    # 4. Local Tests
    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    Test-Endpoint "GET /health" "GET" "/health"
    Test-Endpoint "GET /news/providers" "GET" "/news/providers"
    Test-Endpoint "GET /news/active" "GET" "/news/active?limit=5"
    Test-Endpoint "GET /news/upcoming" "GET" "/news/upcoming?limit=5"
    Test-Endpoint "POST /trades/open" "POST" "/trades/open" @{ symbol="AAPL"; side="buy"; quantity=10; capturedAtUtc=$now }
    Test-Endpoint "GET /trades/open" "GET" "/trades/open"
    Test-Endpoint "GET /model-version" "GET" "/model-version"
    Test-Endpoint "GET /performance" "GET" "/performance"
    Test-Endpoint "POST /log-signal" "POST" "/log-signal" @{ signal="buy"; symbol="AAPL"; timestamp=$now }
    Test-Endpoint "POST /log-rejected-signal" "POST" "/log-rejected-signal" @{ reason="limit"; symbol="AAPL"; timestamp=$now }
    Test-Endpoint "POST /log-trade" "POST" "/log-trade" @{ action="buy"; symbol="AAPL"; price=150 }
    Test-Endpoint "POST /risk-check" "POST" "/risk-check" @{ symbol="AAPL"; side="buy"; price=150; size=10 }
    Test-Endpoint "POST /portfolio/evaluate" "POST" "/portfolio/evaluate" @{ holdings=@() }
    Test-Endpoint "POST /signal" "POST" "/signal" @{ type="entry"; data=@{} }

    # 5. External FMP Tests
    $env = Get-Content .env | ConvertFrom-StringData
    $fmpKey = $env.FMP_API_KEY
    $fmpBase = $env.FMP_BASE_URL
    
    Test-External "FMP stable current (header)" "$fmpBase/api/v3/economic_calendar" @{"apikey"=$fmpKey}
    Test-External "FMP stable hist (header)" "$fmpBase/api/v3/economic_calendar?from=2024-01-01&to=2024-01-31" @{"apikey"=$fmpKey}
    Test-External "FMP stable hist (query)" "$fmpBase/api/v3/economic_calendar?from=2024-01-01&to=2024-01-31&apikey=$fmpKey"
    Test-External "FMP v3 current (query)" "$fmpBase/api/v3/economic_calendar?apikey=$fmpKey"
    Test-External "FMP v3 hist (query)" "$fmpBase/api/v3/economic_calendar?from=2024-01-01&to=2024-01-31&apikey=$fmpKey"

    # 6. Report
    $results | ConvertTo-Json | Out-File "api_test_report.json"
    $results | Format-Table -AutoSize
} finally {
    if ($jobId) { 
        Stop-Process -Id $jobId -Force -ErrorAction SilentlyContinue 
    }
}
