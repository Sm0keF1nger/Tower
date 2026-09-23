@echo off
setlocal
cd /d "%~dp0"

echo WARNING: This removes local Keycloak data and imports the realm again.
echo Any manual Keycloak changes made after the first start will be lost.
choice /C YN /M "Continue"
if errorlevel 2 exit /b 0

docker compose down
docker volume rm tower_keycloak_data 2>nul
docker compose up -d
if errorlevel 1 (
    echo ERROR: Tower could not be restarted.
    pause
    exit /b 1
)

echo Keycloak data reset completed.
pause
endlocal
