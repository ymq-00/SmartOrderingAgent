@echo off
rem ============================================================
rem  SmartOrderingAgent - One Click Start
rem  Starts Redis + backend(8000) + frontend(3000), opens browser.
rem ============================================================
cd /d "%~dp0"
title SmartOrderingAgent

echo ============================================================
echo    SmartOrderingAgent - Smart Ordering System
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found.
    echo         Run "uv sync" in the project root first.
    echo.
    pause
    exit /b 1
)

call "%~dp0scripts\start-env.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Environment setup failed. See messages above.
    pause
    exit /b 1
)
echo.

call "%~dp0scripts\start-api.bat"
timeout /t 6 /nobreak >nul

call "%~dp0scripts\start-ui.bat"
timeout /t 8 /nobreak >nul

echo Opening browser ...
start "" "http://localhost:3000"

echo.
echo ============================================================
echo   All started.
echo.
echo   Frontend : http://localhost:3000      ^<-- open this one
echo   API docs : http://127.0.0.1:8000/docs
echo.
echo   Stop     : close the [API-8000] and [UI-3000] windows
echo   Redis    : keep it running in the background
echo ============================================================
echo.
pause
