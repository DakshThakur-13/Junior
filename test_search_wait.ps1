Start-Sleep -Seconds 5
Write-Host "Testing search API..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/research/sources/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"query": "rape", "limit": 200}' `
        -UseBasicParsing

    $json = $response.Content | ConvertFrom-Json
    Write-Host "✅ Total results: $($json.results.Count)" -ForegroundColor Green
    Write-Host "`nFirst 5 results:"
    $json.results | Select-Object -First 5 | ForEach-Object { 
        Write-Host "  - [$($_.type)] $($_.title)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}
