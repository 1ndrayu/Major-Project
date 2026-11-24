@echo off
title Service Reliability Platform - Live Dashboard
echo ========================================================================
echo    SERVICE RELIABILITY PLATFORM - AUTOMATED INCIDENT REMEDIATION
echo    Author: Dhruv Oswal (A70405223051)
echo ========================================================================
echo.
echo [*] Checking runtime dependencies...
python -c "import torch, fastapi, uvicorn, networkx, pydantic" 2>nul
if %errorlevel% neq 0 (
    echo [!] Missing dependencies. Installing from requirements.txt...
    pip install -r requirements.txt
)

echo.
echo [*] Starting web application on http://127.0.0.1:8000 ...
echo [*] Automatically opening site in default browser...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"
echo.
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
pause
