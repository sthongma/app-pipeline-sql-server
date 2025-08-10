@echo off
echo =============================================
echo  Pipeline Bronze App - GUI Mode
echo =============================================
echo.

REM Change working directory to the script folder
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
echo.
echo Common installation locations checked:
echo - System PATH
echo - Python Launcher (py)
echo - %LOCALAPPDATA%\Programs\Python\
echo - C:\Python*\
pause
exit /b 1

:python_found
echo Python found
%PYTHON_EXE% --version
echo Using interpreter: %PYTHON_EXE%

REM Check requirements
echo.
echo Checking dependencies...
%PYTHON_EXE% -c "import customtkinter, sqlalchemy, pyodbc, pandas, bcpandas" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing, installing...
    call install_requirements.bat
    if errorlevel 1 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
    echo Re-checking dependencies...
    %PYTHON_EXE% -c "import customtkinter, sqlalchemy, pyodbc, pandas, bcpandas" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Dependencies still missing. Please check your Python environment.
        %PYTHON_EXE% -c "import sys; print('Interpreter:', sys.executable); print('Sys.path:', sys.path)"
        pause
        exit /b 1
    )
) else (
    echo Dependencies ready
)

echo.
echo =============================================
echo  Starting GUI Application
echo =============================================
echo.
echo Opening GUI... (Application window will appear)

REM Run GUI application (no console window after GUI opens)
start "" %PYTHON_EXE% pipeline_gui_app.py

REM Display message and close console
echo.
echo GUI Application started
echo Console window will close in 3 seconds...
echo.

REM Wait 3 seconds then close
timeout /t 3 /nobreak >nul

REM Close console window automatically
exit