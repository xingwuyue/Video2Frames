@echo off
title SpriteSheet Launcher
echo ========================================
echo Starting SpriteSheet Tool...
echo ========================================
echo.

echo [1/2] Starting Backend...
cd /d "%~dp0backend"
start "SpriteSheet Backend" cmd.exe /k "uv run uvicorn app.main:app --host 127.0.0.1 --port 8765"

echo [2/2] Starting Frontend...
cd /d "%~dp0frontend"
start "SpriteSheet Frontend" cmd.exe /k "npm run dev"

cd /d "%~dp0"
echo.
echo ========================================
echo All services have been launched!
echo.
echo 1. The backend is running on 127.0.0.1:8765
echo 2. The frontend will open in your browser shortly.
echo.
echo You can close this launcher window safely.
echo To completely stop the tool, close the two newly opened black windows.
echo ========================================
pause
