@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo   Tower - starting system
echo ================================================
echo.

echo [1/3] Checking Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker Engine is not running.
    echo Start Docker Desktop and wait until the engine is ready.
    echo Then run this file again.
    echo.
    pause
    exit /b 1
)

echo [2/3] Starting Keycloak, backend and frontend...
docker compose up -d
if errorlevel 1 (
    echo.
    echo ERROR: Tower containers could not be started.
    echo Run logs-tower.bat to inspect the logs.
    echo If dependencies changed, run rebuild-tower.bat.
    echo.
    pause
    exit /b 1
)

echo [3/3] Waiting for the web application...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddMinutes(3); $ok=$false; while((Get-Date)-lt $deadline){ try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000' -TimeoutSec 3; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){$ok=$true;break} } catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){exit 1}"

if errorlevel 1 (
    echo.
    echo Containers were started, but the frontend did not answer yet.
    echo Check: docker compose ps
    echo Logs:  logs-tower.bat
    echo.
    pause
    exit /b 1
)

echo.
echo Tower is ready.
echo.
start "" "http://localhost:3000"
timeout /t 2 >nul
endlocal
