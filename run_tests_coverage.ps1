# Run Tests with Coverage
# This script runs the pytest suite with coverage reporting

Write-Host "`n=== Running Junior Test Suite with Coverage ===" -ForegroundColor Cyan

# Activate virtual environment if not already activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "$PSScriptRoot\.venv\Scripts\Activate.ps1"
}

# Run pytest with coverage
Write-Host "`nRunning tests with coverage..." -ForegroundColor Green
pytest

# Check if htmlcov directory was created
if (Test-Path "htmlcov\index.html") {
    Write-Host "`n=== Coverage Report Generated ===" -ForegroundColor Green
    Write-Host "HTML Report: htmlcov\index.html" -ForegroundColor Cyan
    Write-Host "XML Report: coverage.xml" -ForegroundColor Cyan
    
    # Ask to open HTML report
    $response = Read-Host "`nOpen coverage report in browser? (Y/N)"
    if ($response -eq "Y" -or $response -eq "y") {
        Start-Process "htmlcov\index.html"
    }
} else {
    Write-Host "`nNote: Coverage report generation may have failed" -ForegroundColor Yellow
}
