@echo off
rem ============================================================
rem  Start frontend Vite in its own window. Skip if already up.
rem  Exits immediately - safe as a VS Code preLaunchTask.
rem ============================================================
cd /d "%~dp0..\ui"

if not exist "node_modules" (
    echo [UI] node_modules missing, running npm install ...
    call npm install
)

netstat -ano | findstr ":3000 " | findstr LISTENING >nul 2>&1
if not errorlevel 1 (
    echo [UI] already running on 3000, skip
    exit /b 0
)

echo [UI] starting dev server on http://localhost:3000 ...
rem npm.cmd is a batch file, start gives it a new console window.
start "UI-3000" npm.cmd run dev
exit /b 0
