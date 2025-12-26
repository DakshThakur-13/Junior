Start-Sleep -Seconds 8
Write-Host "`n🧪 Testing rebuilt search system..." -ForegroundColor Cyan
Write-Host "=" * 60

try {
    # Test 1: Search for "rape"
    Write-Host "`n📝 Test 1: Searching for 'rape'..." -ForegroundColor Yellow
    $response1 = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/research/sources/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"query": "rape", "limit": 200}' `
        -UseBasicParsing
    
    $json1 = $response1.Content | ConvertFrom-Json
    Write-Host "✅ Results: $($json1.results.Count)" -ForegroundColor Green
    if ($json1.results.Count -gt 0) {
        Write-Host "First 3 results:"
        $json1.results | Select-Object -First 3 | ForEach-Object {
            Write-Host "  - [$($_.type)] $($_.title)" -ForegroundColor Cyan
        }
    }
    
    # Test 2: Search for "pocso"
    Write-Host "`n📝 Test 2: Searching for 'pocso'..." -ForegroundColor Yellow
    $response2 = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/research/sources/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"query": "pocso", "limit": 200}' `
        -UseBasicParsing
    
    $json2 = $response2.Content | ConvertFrom-Json
    Write-Host "✅ Results: $($json2.results.Count)" -ForegroundColor Green
    if ($json2.results.Count -gt 0) {
        Write-Host "First 3 results:"
        $json2.results | Select-Object -First 3 | ForEach-Object {
            Write-Host "  - [$($_.type)] $($_.title)" -ForegroundColor Cyan
        }
    }
    
    # Test 3: Empty search (should return all catalog)
    Write-Host "`n📝 Test 3: Empty search (catalog only)..." -ForegroundColor Yellow
    $response3 = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/research/sources/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"query": "", "limit": 200}' `
        -UseBasicParsing
    
    $json3 = $response3.Content | ConvertFrom-Json
    Write-Host "✅ Results: $($json3.results.Count)" -ForegroundColor Green
    
    Write-Host "`n" + "=" * 60
    Write-Host "✅ ALL TESTS COMPLETED" -ForegroundColor Green
    Write-Host "=" * 60
    
} catch {
    Write-Host "`n❌ ERROR: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
