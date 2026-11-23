@echo off
title Self-Healing Software Ecosystem - Live Dashboard
echo ========================================================================
echo    SELF-HEALING SOFTWARE ECOSYSTEM (B.TECH MAJOR PROJECT 2026-27)
echo    Amity University Maharashtra - Department of Computer Science
echo    Author: Dhruv Oswal (A70405223051)
echo ========================================================================
echo.
echo [*] Checking dependencies...
python -c "import torch, fastapi, uvicorn, networkx, pydantic" 2>nul
if %errorlevel% neq 0 (
    echo [!] Missing dependencies. Installing from requirements.txt...
    pip install -r requirements.txt
)

echo.
echo [*] Starting Live FastAPI Web Control Plane...
echo [*] Dashboard URL: http://127.0.0.1:8000
echo.
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
pause
