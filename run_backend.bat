@echo off
title Significia Backend - Developer Server
echo.
echo 🚀 Starting Significia Backend...
echo.

REM Set current directory to the script's directory
cd %~dp0

REM Check if venv exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Please run:
    echo    python -m venv venv
    pause
    exit /b
)

REM Run backend on port 8001 (standard for Significia local dev)
echo 🔧 Starting Uvicorn on 8001...
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app

echo.
echo 👋 Backend server stopped.
pause
