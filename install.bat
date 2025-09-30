@echo off
setlocal enabledelayedexpansion

echo ============================================================================
echo  Django SyncService Installer
echo  - Creates virtual environment
echo  - Installs Python dependencies
echo  - Sets up Django database
echo ============================================================================
echo.

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ and add to PATH
    pause
    exit /b 1
)

echo Using Python: 
python --version
echo.

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Create virtual environment if missing
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment
        echo Try: python -m pip install --upgrade pip
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% neq 0 (
    echo WARNING: Pip upgrade had issues, continuing anyway...
)

REM Install requirements
echo.
echo Installing requirements...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Some packages failed to install
    echo.
    echo Common issues:
    echo - sqlanydb requires SAP SQL Anywhere client installed
    echo - pyodbc/mysqlclient may need system libraries
    echo.
    echo Try installing packages one by one:
    echo   pip install Django
    echo   pip install PyJWT
    echo   pip install requests
    echo   pip install psutil
    echo   pip install sqlanydb
    echo.
    pause
    exit /b 1
)

echo.
echo All packages installed successfully!

REM Check if Django project exists
if exist "django_sync\manage.py" (
    echo.
    echo Setting up Django database...
    cd django_sync
    python manage.py makemigrations --noinput
    python manage.py migrate --noinput
    cd ..
    echo Django database setup complete
) else if exist "manage.py" (
    echo.
    echo Setting up Django database...
    python manage.py makemigrations --noinput
    python manage.py migrate --noinput
    echo Django database setup complete
) else (
    echo WARNING: manage.py not found, skipping Django migrations
)

REM Create .env file if missing
if not exist ".env" (
    echo.
    echo Creating .env file with default settings...
    (
        echo DB_DSN=pktc
        echo DB_UID=dba
        echo DB_PWD=sql
        echo JWT_SECRET=change-this-secret-key-in-production
        echo JWT_ALGO=HS256
        echo PAIR_PASSWORD=IMC-MOBILE
    ) > .env
    echo .env file created - PLEASE UPDATE WITH YOUR ACTUAL CREDENTIALS
)

echo.
echo ============================================================================
echo Installation complete!
echo ============================================================================
echo.
echo Next steps:
echo 1. Update credentials in .env file
echo 2. Run: start.bat (or python SyncService.py)
echo 3. Access server at: http://localhost:8000
echo.
echo IMPORTANT: Update .env with your actual database password!
echo.
pause
endlocal