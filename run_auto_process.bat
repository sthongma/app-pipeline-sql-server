@echo off
REM Automated File Processing CLI
REM Standalone program for automatic file processing

echo ========================================
echo     Automated File Processing CLI
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)

REM Check if auto_process_cli.py exists
if not exist "auto_process_cli.py" (
    echo ERROR: auto_process_cli.py not found
    pause
    exit /b 1
)

REM Run CLI program
if "%~1"=="" (
    echo Running with last folder from settings...
    echo.
    python auto_process_cli.py
) else (
    echo Running with folder: %~1
    echo.
    python auto_process_cli.py "%~1"
)

echo.
echo Processing completed
pause
