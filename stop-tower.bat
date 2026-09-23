@echo off
setlocal
cd /d "%~dp0"

echo Stopping Tower...
docker compose stop
if errorlevel 1 (
    echo ERROR: Containers could not be stopped.
    pause
    exit /b 1
)

echo Tower stopped. Data and containers were preserved.
timeout /t 2 >nul
endlocal
