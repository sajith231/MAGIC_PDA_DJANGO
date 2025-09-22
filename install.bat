@echo off
echo ========================================
echo Django SyncService Installation Script
echo ========================================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python found: 
python --version

:: Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv

:: Check if virtual environment was created
if not exist "venv\" (
    echo ERROR: Failed to create virtual environment
    echo Please check Python installation
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

:: Create requirements.txt if it doesn't exist
if not exist "requirements.txt" (
    echo Creating basic requirements.txt...
    echo Django^>=4.2.0,^<5.0> requirements.txt
    echo sqlanydb^>=1.0.0>> requirements.txt
    echo requests^>=2.28.0>> requirements.txt
    echo python-dateutil^>=2.8.0>> requirements.txt
    echo pytz^>=2023.3>> requirements.txt
    echo asgiref^>=3.6.0>> requirements.txt
    echo sqlparse^>=0.4.0>> requirements.txt
    echo tzdata^>=2023.3>> requirements.txt
)

:: Install requirements
echo.
echo Installing project dependencies...
pip install -r requirements.txt

:: Check if Django is installed
python -c "import django; print('Django version:', django.get_version())" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Django installation may have failed
    echo Attempting to install Django directly...
    pip install Django
)

:: Create database tables if Django project exists
if exist "django_sync\" (
    echo.
    echo Setting up Django database...
    cd django_sync
    if exist "manage.py" (
        python manage.py makemigrations
        python manage.py migrate
    )
    cd ..
)

:: Create config.json if it doesn't exist
if not exist "config.json" (
    echo Creating default configuration...
    echo {> config.json
    echo   "ip": "127.0.0.1",>> config.json
    echo   "port": 8000,>> config.json
    echo   "dsn": "pktc",>> config.json
    echo   "auto_start": true,>> config.json
    echo   "log_level": "INFO",>> config.json
    echo   "all_ips": ["127.0.0.1", "192.168.1.53"]>> config.json
    echo }>> config.json
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo To start the application:
echo 1. Double-click SyncService.py
echo 2. Or run: python SyncService.py
echo 3. Or double-click start.bat
echo.
echo Your application will be available at:
echo http://127.0.0.1:8000
echo.
pause