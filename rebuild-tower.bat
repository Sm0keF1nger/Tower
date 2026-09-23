@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo   Tower - rebuilding Docker images
echo ================================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Engine is not running.
    echo Start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Rebuilding backend/frontend and starting Tower...
docker compose up -d --build
if errorlevel 1 (
    echo ERROR: Rebuild failed.
    echo Run logs-tower.bat for details.
    pause
    exit /b 1
)

echo Rebuild completed.
start "" "http://localhost:3000"
timeout /t 2 >nul
endlocal
