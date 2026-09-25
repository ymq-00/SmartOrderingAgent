@echo off
rem ============================================================
rem  Used by VS Code preLaunchTask: prepare infra (Redis + FAQ).
rem  Exits immediately, does not hold the terminal.
rem  NOTE: keep this file pure ASCII + CRLF. Chinese text here
rem  gets mis-decoded as GBK and breaks the batch parser.
rem ============================================================
cd /d "%~dp0.."

echo [1/2] Check Redis on port 6380 ...
netstat -ano | findstr ":6380 " | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo        not running, starting in background ...
    start "" /min "D:\ZenTao\bin\redis\redis-server.exe" --port 6380 --bind 127.0.0.1 --appendonly no --dir "%TEMP%"
    timeout /t 3 /nobreak >nul
) else (
    echo        already running, skip
)

echo [2/2] Sync FAQ data into Redis ...
".venv\Scripts\python.exe" agent\redis_data_sync.py
if errorlevel 1 (
    echo        [FAILED] FAQ sync error, please check Redis
    exit /b 1
)
echo        done
exit /b 0
