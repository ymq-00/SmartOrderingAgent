@echo off
rem ============================================================
rem  Start backend FastAPI in its own window. Skip if already up.
rem  No breakpoint support here - use VS Code F5 for debugging.
rem ============================================================
cd /d "%~dp0.."

netstat -ano | findstr ":8000 " | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [API] already running on 8000, skip
    exit /b 0
)

echo [API] starting FastAPI, docs at http://127.0.0.1:8000/docs ...
rem start on an .exe gives it its own console window.
rem Avoid cmd /k here - nested quotes in start are error prone.
start "API-8000" .venv\Scripts\python.exe run.py
exit /b 0
