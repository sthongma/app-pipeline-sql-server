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

REM Install essential packages first
echo.
echo Installing essential packages (setuptools)...
python -m pip install --upgrade setuptools

REM Verify Python deps
echo.
echo Verifying Python packages (pandas, sqlalchemy, pyodbc)...
python -c "import pandas, sqlalchemy, pyodbc; print('Python deps OK')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Some Python packages are missing. Re-installing requirements...
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -r requirements.txt
    python -m pip install --upgrade setuptools
)

REM Check for ODBC Driver
echo.
echo Checking for ODBC Driver for SQL Server...
reg query "HKEY_LOCAL_MACHINE\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 17 for SQL Server" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    reg query "HKEY_LOCAL_MACHINE\SOFTWARE\ODBC\ODBCINST.INI\ODBC Driver 18 for SQL Server" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ODBC Driver not found. Attempting to install Microsoft ODBC Driver for SQL Server.

        REM Try winget first
        where winget >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            echo Installing Microsoft ODBC Driver for SQL Server via winget...
            winget install --id Microsoft.MicrosoftODBCDriver18 --silent --accept-package-agreements --accept-source-agreements
            if %ERRORLEVEL% NEQ 0 (
                winget install --id Microsoft.MicrosoftODBCDriver17 --silent --accept-package-agreements --accept-source-agreements
            )
        ) else (
            REM Try Chocolatey if available
            where choco >nul 2>&1
            if %ERRORLEVEL% EQU 0 (
                echo Installing via Chocolatey...
                choco install mssql-odbcdriver -y
            ) else (
                echo Could not find winget or choco. Please install manually:
                echo  - ODBC Driver for SQL Server: https://aka.ms/msodbcsql
            )
        )
    ) else (
        echo ODBC Driver 18 for SQL Server is available.
    )
) else (
    echo ODBC Driver 17 for SQL Server is available.
)

echo.
echo Installation completed successfully!
echo You can now run the application using:
echo - run_pipeline_gui.bat (GUI)
echo.
