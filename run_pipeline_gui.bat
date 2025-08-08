@echo off
echo =============================================
echo  Pipeline Bronze App - GUI Mode
echo =============================================
echo.

REM Change working directory to the script folder
cd /d "%~dp0"

REM Set Python executable to Microsoft Store version
set "PYTHON_EXE=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"

REM Check if Microsoft Store Python exists
if not exist "%PYTHON_EXE%" (
    echo Error: Python from Microsoft Store not found
    echo Please install Python from Microsoft Store
    echo Expected location: %PYTHON_EXE%
    pause
    exit /b 1
)

:python_found
echo Python found
%PYTHON_EXE% --version

REM Check requirements
echo.
echo Checking dependencies...
%PYTHON_EXE% -c "import customtkinter, sqlalchemy, pyodbc, pandas" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing, installing...
    call install_requirements.bat
    if errorlevel 1 (
        echo Failed to install dependencies
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