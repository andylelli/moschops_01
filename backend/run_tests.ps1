$reportPath = "C:\moschops_01\backend\api_test_report.json"
$outLog = "C:\moschops_01\backend\stdout.log"
$errLog = "C:\moschops_01\backend\stderr.log"

# Build backend
# Write-Host "Building backend..."
npm run build 2>&1 > $null

# Start backend
$process = Start-Process node -ArgumentList "dist/index.js" -PassThru -RedirectStandardOutput $outLog -RedirectStandardError $errLog -NoNewWindow
# Wait for backend to start
Start-Sleep -Seconds 5

$results = @()

function Test-Endpoint($name, $method, $url, $body = $null) {
    try {
        $params = @{
            Uri = "http://localhost:3000$url"
            Method = $method
            ContentType = "application/json"
            ErrorAction = "Stop"
        }
        if ($body) { $params.Body = ($body | ConvertTo-Json) }
        $resp = Invoke-WebRequest @params
        return @{ name=$name; statusCode=$resp.StatusCode; ok=$true; summary="Success" }
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        return @{ name=$name; statusCode=$status; ok=$false; summary=$_.Exception.Message }
    }
}

function Test-External($name, $url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -Method Get -ErrorAction Stop
        return @{ name=$name; statusCode=$resp.StatusCode; ok=$true; summary="Success" }
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        return @{ name=$name; statusCode=$status; ok=$false; summary=$_.Exception.Message }
    }
}

# Internal Checks
$results += Test-Endpoint "GET /health" "GET" "/health"
$results += Test-Endpoint "GET /news/providers" "GET" "/news/providers"
$results += Test-Endpoint "GET /news/active?limit=5" "GET" "/news/active?limit=5"
$results += Test-Endpoint "GET /news/upcoming?limit=5" "GET" "/news/upcoming?limit=5"
$results += Test-Endpoint "POST /trades/open" "POST" "/trades/open" @{ symbol="AAPL"; quantity=1; side="buy" }
$results += Test-Endpoint "GET /trades/open" "GET" "/trades/open"
$results += Test-Endpoint "GET /model-version" "GET" "/model-version"
$results += Test-Endpoint "GET /performance" "GET" "/performance"
$results += Test-Endpoint "POST /log-signal" "POST" "/log-signal" @{ signal="buy"; symbol="AAPL" }
$results += Test-Endpoint "POST /log-rejected-signal" "POST" "/log-rejected-signal" @{ signal="buy"; symbol="AAPL"; reason="risk" }
$results += Test-Endpoint "POST /log-trade" "POST" "/log-trade" @{ symbol="AAPL"; quantity=1; price=150 }
$results += Test-Endpoint "POST /risk-check" "POST" "/risk-check" @{ symbol="AAPL"; quantity=1 }
$results += Test-Endpoint "POST /portfolio/evaluate" "POST" "/portfolio/evaluate" @{}
$results += Test-Endpoint "POST /signal" "POST" "/signal" @{ symbol="AAPL" }

# External Checks (FMP)
$fmpKey = "voAQ0dKYsSQGlQGtzRo3ji0A8DhHEzOI"
$results += Test-External "stable current/header" "https://financialmodelingprep.com/api/v3/quote/AAPL?apikey=$fmpKey"
$results += Test-External "stable historical/header" "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?apikey=$fmpKey"
$results += Test-External "stable historical/query fallback" "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?timeseries=5&apikey=$fmpKey"
$results += Test-External "v3 current/query" "https://financialmodelingprep.com/api/v3/quote/AAPL?apikey=$fmpKey"
$results += Test-External "v3 historical/query" "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?apikey=$fmpKey"

$results | ConvertTo-Json -Compress | Out-File -FilePath $reportPath -Encoding utf8
Write-Host "REPORT_WRITTEN"

# Stop backend
Stop-Process -Id $process.Id -Force
