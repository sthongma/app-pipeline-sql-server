@echo off
echo =============================================
echo  Pipeline Bronze App - Move Old Files
echo =============================================
echo.

REM Change working directory to the script folder
cd /d "%~dp0"

REM Set Python executable variable
set "PYTHON_EXE="

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
) do call :check_python "%%i"

goto :after_python_check

:check_python
if exist %1 (
    set "PYTHON_EXE=%~1"
    goto :python_found
)
exit /b

:after_python_check

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

REM Check requirements
echo.
echo Checking dependencies...
%PYTHON_EXE% -c "import send2trash, pandas" >nul 2>&1
if errorlevel 1 (
    echo Dependencies missing, installing...
    %PYTHON_EXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies
        exit /b 1
    )
) else (
    echo Dependencies ready
)

echo.
echo =============================================
echo  Starting Move Old Files Application
echo =============================================
echo.

REM Run Move Old Files CLI application
%PYTHON_EXE% move_old_files_cli_app.py %*

REM Display results
echo.
echo =============================================
if errorlevel 1 (
    echo Move Old Files Application finished with errors
) else (
    echo Move Old Files Application completed successfully
)
echo =============================================

REM Wait for user to press key before closing window
echo.
echo Press Enter to close window...
pause >nul
