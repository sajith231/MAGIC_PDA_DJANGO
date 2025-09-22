@echo off
title Django SyncService

echo ========================================
echo Django SyncService - Quick Start
echo ========================================

:: Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found!
    echo Please run install.bat first
    echo.
    echo Double-click install.bat to set up the project
    pause
    exit /b 1
)

:: Check if SyncService.py exists
if not exist "SyncService.py" (
    echo SyncService.py not found!
    echo Make sure you're in the correct directory
    pause
    exit /b 1
)

:: Activate virtual environment and run
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting SyncService...
echo.
python SyncService.py

echo.
echo SyncService has stopped
pause