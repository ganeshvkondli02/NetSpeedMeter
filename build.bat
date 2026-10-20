@echo off
setlocal
title NetSpeedOverlay - Windows Executable Builder

REM Always build from the folder containing this script.
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] Could not open the project folder.
    pause
    exit /b 1
)

echo ============================================================
echo       NetSpeedOverlay - Executable Builder
echo ============================================================
echo.
echo Project folder: %CD%
echo.

REM Check required source files.
for %%F in (main.py config.py overlay.py speed_monitor.py tray.py settings_dialog.py autostart.py requirements.txt NetSpeedOverlay.spec assets\app-icon.ico assets\app-icon.png) do (
    if not exist "%%F" (
        echo [ERROR] Missing required file: %%F
        pause
        exit /b 1
    )
)

REM Check that Python is available.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.11 or newer and add it to PATH.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/3] Building executable using the portable spec file...
python -m PyInstaller --noconfirm --clean NetSpeedOverlay.spec
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Review the messages above.
    pause
    exit /b 1
)

if not exist "dist\NetSpeedOverlay.exe" (
    echo [ERROR] Build reported success, but the EXE was not found.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL
echo ============================================================
echo Executable: "%CD%\dist\NetSpeedOverlay.exe"
echo.
start "" explorer "%CD%\dist"
pause
