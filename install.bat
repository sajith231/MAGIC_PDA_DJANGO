@echo off
setlocal enabledelayedexpansion

REM ----------------------------
REM install.bat - create venv + install requirements
REM ----------------------------

echo ============================================================================
echo  SyncProject installer
echo  - Creates a venv, upgrades pip, installs packages from full_requirements.txt
echo ============================================================================
echo.

REM 1) choose python
echo Checking for python launcher (py)...
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    echo Using py launcher.
    rem try py -3.13 then py -3
    py -3.13 -c "import sys; print(sys.executable)" >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYCMD=py -3.13"
    ) else (
        py -3 -c "import sys; print(sys.executable)" >nul 2>nul
        if %ERRORLEVEL%==0 (
            set "PYCMD=py -3"
        ) else (
            set "PYCMD=py"
        )
    )
) else (
    echo py launcher not found, falling back to system python.
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYCMD=python"
    ) else (
        echo ERROR: Could not find Python. Please install Python 3.11+ and re-run.
        pause
        exit /b 1
    )
)

echo Using: %PYCMD%
echo.

REM 2) ensure full_requirements.txt exists
if not exist "full_requirements.txt" (
    echo ERROR: full_requirements.txt not found in %CD%.
    echo Please copy full_requirements.txt here and run this installer again.
    pause
    exit /b 1
)

REM 3) create venv if missing
if not exist "venv\Scripts\activate" (
    echo Creating virtual environment (venv)...
    %PYCMD% -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

REM 4) activate venv for this script
call "venv\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate venv.
    pause
    exit /b 1
)

REM 5) upgrade pip, setuptools, wheel
echo Upgrading pip, setuptools and wheel...
python -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to fully upgrade pip/setuptools/wheel (continuing)...
)

REM 6) install from requirements
echo Installing packages from full_requirements.txt ...
set "FAILLOG=install_failures.log"
if exist "%FAILLOG%" del "%FAILLOG%"

REM First try a normal install
python -m pip install -r full_requirements.txt
if %ERRORLEVEL%==0 (
    echo.
    echo All packages installed successfully.
    echo.
    goto post_install
)

REM If we get here, pip failed. Capture details and try limited fallbacks.
echo.
echo WARNING: pip install failed. Capturing output to %FAILLOG% and attempting targeted fallbacks...
echo Attempt at %DATE% %TIME% > "%FAILLOG%"
python -m pip install -r full_requirements.txt >> "%FAILLOG%" 2>&1

REM Try a second pass: install problematic binary packages with only-binary (often helps for pillow/cryptography)
echo Trying a fallback install for commonly problematic packages...
python -m pip install --only-binary=:all: pillow cryptography psycopg2-binary PyMySQL >> "%FAILLOG%" 2>&1

REM Try again full install (some packages may have been satisfied)
python -m pip install -r full_requirements.txt >> "%FAILLOG%" 2>&1

REM Report summary
echo.
echo ========== INSTALL SUMMARY ==========
findstr /C:"ERROR:" "%FAILLOG%" >nul 2>nul
if %ERRORLEVEL%==0 (
    echo Some packages failed to install. See %FAILLOG% for full pip output.
    echo Common fixes:
    echo  - Ensure the target laptop has the right Python (recommended: Python 3.11/3.13).
    echo  - For packages like pyodbc/mysqlclient/sqlanydb install the system DB driver / SDK first.
    echo  - Consider creating a wheelhouse on your machine and copying it to the target machine.
    echo.
    echo If you want to create a wheelhouse on this machine, run:
    echo    python -m pip download -r full_requirements.txt -d wheelhouse
    echo Then copy the wheelhouse folder to the target laptop and run:
    echo    pip install --no-index --find-links wheelhouse -r full_requirements.txt
) else (
    echo All requirements appear to be installed (no ERROR lines in %FAILLOG%).
)

:post_install
REM 7) run Django migrations if manage.py exists
if exist "manage.py" (
    echo Running Django migrations (manage.py in project root)...
    python manage.py makemigrations --noinput || echo "makemigrations returned non-zero (continuing)..."
    python manage.py migrate --noinput || echo "migrate returned non-zero (continuing)..."
) else if exist "django_sync\manage.py" (
    echo Running Django migrations (django_sync/manage.py)...
    pushd django_sync
    python manage.py makemigrations --noinput || echo "makemigrations returned non-zero (continuing)..."
    python manage.py migrate --noinput || echo "migrate returned non-zero (continuing)..."
    popd
) else (
    echo No manage.py found; skipping migrations.
)

REM 8) done
echo.
echo INSTALLER finished. See %FAILLOG% if any failures occurred.
echo You can start the project with start.bat or runserver manually.
pause
endlocal
