# PowerShell Startup Script for Service Reliability Platform
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   SERVICE RELIABILITY PLATFORM - AUTOMATED INCIDENT REMEDIATION" -ForegroundColor Cyan
Write-Host "   Author: Dhruv Oswal (A70405223051)" -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Starting web application on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/c timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000" -WindowStyle Hidden
Write-Host "[*] Automatically opening default browser..." -ForegroundColor White
Write-Host ""

python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
