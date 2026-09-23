@echo off
setlocal
cd /d "%~dp0"

echo Tower service status:
echo.
docker compose ps
echo.
pause
endlocal
