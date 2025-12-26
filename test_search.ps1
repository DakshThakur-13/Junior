$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/research/sources/search" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"query": "rape", "limit": 200}' `
    -UseBasicParsing

$json = $response.Content | ConvertFrom-Json
Write-Host "Total results: $($json.results.Count)"
Write-Host "Results:"
$json.results | ForEach-Object { Write-Host "  - $($_.title)" }
