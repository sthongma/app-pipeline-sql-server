@echo off
echo ========================================
echo     Column Mapper Tool - ML Enhanced
echo ========================================
echo.

REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Set Python executable variable
set "PYTHON_EXE="

REM Prefer project virtual environment Python if available
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    goto :python_found
)

REM Try to find Python in common locations
REM First try system PATH
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :python_found
)

REM Try py launcher (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    goto :python_found
)

REM Try common installation paths
for %%i in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
) do (
    if exist "%%i" (
        set "PYTHON_EXE=%%i"
        goto :python_found
    )
)

REM If still not found, show error
echo Error: Python not found in system
echo Please install Python or add Python to PATH
pause
exit /b 1

:python_found
echo Python found: %PYTHON_EXE%

REM Check if column_mapper_cli.py exists
if not exist "column_mapper_tool\column_mapper_cli.py" (
    echo ERROR: column_mapper_cli.py not found in column_mapper_tool folder
    pause
    exit /b 1
)

REM Check basic dependencies
echo Checking basic dependencies...
%PYTHON_EXE% -c "import pandas, json, os" >nul 2>&1
if errorlevel 1 (
    echo Basic dependencies missing, installing...
    call install_requirements.bat
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check ML dependencies (optional)
echo Checking ML dependencies (optional)...
%PYTHON_EXE% -c "import sentence_transformers, sklearn" >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: ML dependencies not found
    echo For enhanced ML features, install:
    echo   pip install sentence-transformers scikit-learn
    echo.
    echo Tool will run with basic string matching only
    echo.
)

echo.
echo ========================================
echo  Starting Column Mapper Tool
echo ========================================
echo.

REM Run Column Mapper CLI
if "%~1"=="" (
    echo Running with last folder from main program...
    echo.
    %PYTHON_EXE% column_mapper_tool\column_mapper_cli.py
) else (
    echo Running with folder: %~1
    echo.
    %PYTHON_EXE% column_mapper_tool\column_mapper_cli.py "%~1"
)

echo.
echo Column mapping completed
pause