@echo off
title NetSpeedOverlay - Quick Launch
echo Starting NetSpeedOverlay...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.11+ and check "Add to PATH".
    pause
    exit /b 1
)

pip install -r requirements.txt >nul 2>&1
start "" pythonw main.py
exit
