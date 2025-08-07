@echo off
echo Installing PipelineBronze Requirements...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
python -m pip install -r requirements.txt

echo.
echo Installation completed successfully!
echo You can now run the application using:
echo - run_pipeline_gui.bat (for GUI version)
echo - run_pipeline_cli.bat (for CLI version)
echo.
echo Press any key to exit...
pause >nul
