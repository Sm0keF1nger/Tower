@echo off
setlocal
cd /d "%~dp0"

echo Press Ctrl+C to stop viewing logs.
echo.
docker compose logs -f --tail=150
endlocal
