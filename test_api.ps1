Write-Host "Testing API endpoint..." -ForegroundColor Cyan

$body = @{
    query = "rape"
    limit = 200
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/research/sources/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "✅ API Response:" -ForegroundColor Green
    Write-Host "   Query: $($response.query)"
    Write-Host "   Total Results: $($response.results.Count)"
    
    if ($response.results.Count -gt 0) {
        Write-Host "`nFirst 5 results:"
        $response.results | Select-Object -First 5 | ForEach-Object {
            Write-Host "   - [$($_.type)] $($_.title)" -ForegroundColor Cyan
        }
    } else {
        Write-Host "❌ NO RESULTS RETURNED!" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ API Error: $_" -ForegroundColor Red
}
