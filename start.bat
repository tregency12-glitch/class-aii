@echo off
title Class AI Launcher
echo ===================================================
echo   🎓 Class AI — Smart Schedule & Notification Portal
echo ===================================================
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo [ERROR] Virtual environment (.venv) not found.
    echo Please install dependencies first:
    echo python -m venv .venv
    echo .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b
)

echo [1/2] Launching Background Worker (LINE Webhook & Notification Scheduler)...
start "Class AI - Background Worker" cmd /k "$env:PYTHONIOENCODING='utf-8'; .venv\Scripts\python.exe -u worker.py"

echo [2/2] Launching Streamlit Web Application...
.venv\Scripts\streamlit run app.py

pause
