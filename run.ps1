# PowerShell Startup Script for Self-Healing Software Ecosystem
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   SELF-HEALING SOFTWARE ECOSYSTEM (B.TECH MAJOR PROJECT 2026-27)" -ForegroundColor Cyan
Write-Host "   Amity University Maharashtra | Indrayu Nilesh Sandbhor (A70405223053)" -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Starting FastAPI Live Control Plane on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[*] Open your browser and navigate to http://127.0.0.1:8000 to interact with the live system." -ForegroundColor White
Write-Host ""

python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
