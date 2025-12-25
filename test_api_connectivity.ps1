# API Connectivity Test Script

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔍 TESTING BACKEND API CONNECTIVITY" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan

# Test 1: Health Endpoint
Write-Host "1️⃣  Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method GET
    Write-Host "   ✅ Health Check: PASSED" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor White
    Write-Host "   Version: $($health.version)" -ForegroundColor White
    Write-Host "   Environment: $($health.environment)" -ForegroundColor White
    Write-Host "`n   📊 Services Status:" -ForegroundColor Cyan
    Write-Host "   Groq API: $($health.services.groq)" -ForegroundColor $(if($health.services.groq -eq 'configured'){'Green'}else{'Red'})
    Write-Host "   Supabase: $($health.services.supabase)" -ForegroundColor $(if($health.services.supabase -eq 'configured'){'Green'}else{'Red'})
    Write-Host "   PII Redaction: $($health.services.pii_redaction)`n" -ForegroundColor $(if($health.services.pii_redaction -eq 'enabled'){'Green'}else{'Yellow'})
} catch {
    Write-Host "   ❌ Health Check: FAILED - $_`n" -ForegroundColor Red
    exit 1
}

# Test 2: List Available Cases
Write-Host "2️⃣  Testing Cases Endpoint..." -ForegroundColor Yellow
try {
    $cases = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/cases" -Method GET
    Write-Host "   ✅ Cases Endpoint: PASSED" -ForegroundColor Green
    Write-Host "   Found $($cases.Count) cases`n" -ForegroundColor White
} catch {
    Write-Host "   ❌ Cases Endpoint: FAILED - $_`n" -ForegroundColor Red
}

# Test 3: Test Groq API directly
Write-Host "3️⃣  Testing Groq API Key..." -ForegroundColor Yellow
$groqKey = (Get-Content .env | Select-String "GROQ_API_KEY=").ToString().Split("=")[1]
try {
    $headers = @{
        "Authorization" = "Bearer $groqKey"
        "Content-Type" = "application/json"
    }
    $response = Invoke-RestMethod -Uri "https://api.groq.com/openai/v1/models" -Method GET -Headers $headers
    Write-Host "   ✅ Groq API Key: VALID" -ForegroundColor Green
    Write-Host "   Available models: $($response.data.Count)`n" -ForegroundColor White
} catch {
    Write-Host "   ❌ Groq API Key: INVALID - $_`n" -ForegroundColor Red
}

# Test 4: Test Perplexity API directly
Write-Host "4️⃣  Testing Perplexity API Key..." -ForegroundColor Yellow
$perplexityKey = (Get-Content .env | Select-String "PERPLEXITY_API_KEY=").ToString().Split("=")[1]
try {
    $headers = @{
        "Authorization" = "Bearer $perplexityKey"
        "Content-Type" = "application/json"
    }
    $body = @{
        "model" = "llama-3.1-sonar-small-128k-online"
        "messages" = @(
            @{
                "role" = "user"
                "content" = "Test"
            }
        )
        "max_tokens" = 10
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "https://api.perplexity.ai/chat/completions" -Method POST -Headers $headers -Body $body
    Write-Host "   ✅ Perplexity API Key: VALID" -ForegroundColor Green
    Write-Host "   Test completion successful`n" -ForegroundColor White
} catch {
    Write-Host "   ⚠️  Perplexity API Key: $_`n" -ForegroundColor Yellow
}

# Test 5: Test Supabase connectivity
Write-Host "5️⃣  Testing Supabase Connectivity..." -ForegroundColor Yellow
$supabaseUrl = (Get-Content .env | Select-String "SUPABASE_URL=").ToString().Split("=")[1]
$supabaseKey = (Get-Content .env | Select-String "^SUPABASE_KEY=").ToString().Split("=")[1]
try {
    $headers = @{
        "apikey" = $supabaseKey
        "Authorization" = "Bearer $supabaseKey"
    }
    $response = Invoke-RestMethod -Uri "$supabaseUrl/rest/v1/" -Method GET -Headers $headers
    Write-Host "   ✅ Supabase: CONNECTED" -ForegroundColor Green
    Write-Host "   URL: $supabaseUrl`n" -ForegroundColor White
} catch {
    Write-Host "   ⚠️  Supabase: $_`n" -ForegroundColor Yellow
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "✅ API CONNECTIVITY TESTS COMPLETE" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan
