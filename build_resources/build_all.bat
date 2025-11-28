@echo off
REM ====================================================================
REM Build Script for SQL Server Pipeline Installer
REM This script automates the entire build process
REM ====================================================================

echo.
echo ====================================================================
echo Building SQL Server Pipeline Installer
echo ====================================================================
echo.

REM Step 1: Create Icon
echo [Step 1/3] Creating application icon from PNG...
echo --------------------------------------------------------------------
python build_resources/create_icon.py
if errorlevel 1 (
    echo [ERROR] Failed to create icon!
    pause
    exit /b 1
)
echo [OK] Icon created successfully
echo.

REM Step 2: Build Executable with PyInstaller
echo [Step 2/3] Building executable with PyInstaller...
echo --------------------------------------------------------------------
echo This may take 5-10 minutes. Please wait...
pyinstaller SQLServerPipeline.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)
echo [OK] Executable built successfully
echo.

REM Step 3: Check if Inno Setup is installed
echo [Step 3/3] Creating Windows installer with Inno Setup...
echo --------------------------------------------------------------------

REM Check for Inno Setup in common locations
set INNO_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set INNO_PATH=C:\Program Files (x86)\Inno Setup 5\ISCC.exe

if "%INNO_PATH%"=="" (
    echo [WARNING] Inno Setup not found!
    echo.
    echo Please install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, run this command manually:
    echo "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_resources\installer_script.iss
    echo.
    pause
    exit /b 1
)

REM Run Inno Setup compiler
"%INNO_PATH%" build_resources\installer_script.iss
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed!
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo Build Complete!
echo ====================================================================
echo.
echo Executable location:  dist\SQLServerPipeline.exe
echo Installer location:   installer_output\SQLServerPipeline_v1.0.0_Setup.exe
echo.
echo You can now distribute the installer file!
echo.
pause
