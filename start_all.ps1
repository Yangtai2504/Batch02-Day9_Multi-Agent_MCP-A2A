$root = $PSScriptRoot

function Start-Agent($name, $module) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "Set-Location '$root'; Write-Host '=== $name ===' -ForegroundColor Cyan; uv run python -m $module"
}

Write-Host "Starting Registry (port 18000)..." -ForegroundColor Yellow
Start-Agent "Registry :18000" "registry"
Start-Sleep -Seconds 2

Write-Host "Starting Tax Agent (port 10102)..." -ForegroundColor Yellow
Start-Agent "Tax Agent :10102" "tax_agent"

Write-Host "Starting Compliance Agent (port 10103)..." -ForegroundColor Yellow
Start-Agent "Compliance Agent :10103" "compliance_agent"
Start-Sleep -Seconds 3

Write-Host "Starting Law Agent (port 10101)..." -ForegroundColor Yellow
Start-Agent "Law Agent :10101" "law_agent"
Start-Sleep -Seconds 3

Write-Host "Starting Customer Agent (port 10100)..." -ForegroundColor Yellow
Start-Agent "Customer Agent :10100" "customer_agent"

Write-Host ""
Write-Host "All services started in separate windows." -ForegroundColor Green
Write-Host "Run test: uv run python test_client.py" -ForegroundColor Green
