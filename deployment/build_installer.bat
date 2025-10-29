@echo off
REM ===================================================================
REM Build Script for SQL Server Pipeline Installer
REM This script automates the entire build process
REM ===================================================================

echo.
echo ========================================
echo SQL Server Pipeline - Build Installer
echo Version 2.2.0
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [1/6] Checking dependencies...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo [2/6] Cleaning previous builds...
echo.

REM Clean previous builds
if exist "..\dist\SQLServerPipeline" rmdir /s /q "..\dist\SQLServerPipeline"
if exist "..\dist\installer" rmdir /s /q "..\dist\installer"
if exist "..\build\SQLServerPipeline" rmdir /s /q "..\build\SQLServerPipeline"

echo [3/6] Building executable with PyInstaller...
echo.

REM Build with PyInstaller
cd ..
pyinstaller --clean build\pipeline_gui_app.spec

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo [4/6] Copying additional files...
echo.

REM Copy additional files to distribution
if not exist "dist\SQLServerPipeline" (
    echo [ERROR] PyInstaller output not found!
    pause
    exit /b 1
)

REM Copy documentation
copy /y "README.md" "dist\SQLServerPipeline\" >nul
copy /y "SECURITY.md" "dist\SQLServerPipeline\" >nul
copy /y "PERFORMANCE.md" "dist\SQLServerPipeline\" >nul
copy /y ".env.example" "dist\SQLServerPipeline\" >nul
copy /y "CHANGELOG.md" "dist\SQLServerPipeline\" >nul

REM Create directories
if not exist "dist\SQLServerPipeline\docs" mkdir "dist\SQLServerPipeline\docs"
if not exist "dist\SQLServerPipeline\logs" mkdir "dist\SQLServerPipeline\logs"
if not exist "dist\SQLServerPipeline\Uploaded_Files" mkdir "dist\SQLServerPipeline\Uploaded_Files"
if not exist "dist\SQLServerPipeline\config" mkdir "dist\SQLServerPipeline\config"

REM Copy monitoring tools
xcopy /e /i /y "monitoring" "dist\SQLServerPipeline\monitoring\" >nul 2>&1

echo [5/6] Creating Inno Setup installer...
echo.

REM Check if Inno Setup is installed
set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%INNO_PATH%" (
    set INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
)

if not exist "%INNO_PATH%" (
    echo.
    echo ========================================
    echo Inno Setup not found!
    echo ========================================
    echo.
    echo Please install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo After installation, run this script again.
    echo.
    echo For now, you can use the portable version in:
    echo   dist\SQLServerPipeline\
    echo.
    pause
    exit /b 0
)

REM Build installer with Inno Setup
"%INNO_PATH%" "build\installer.iss"

if %errorlevel% neq 0 (
    echo [ERROR] Inno Setup build failed!
    pause
    exit /b 1
)

echo.
echo [6/6] Build completed successfully!
echo.
echo ========================================
echo Build Summary
echo ========================================
echo.
echo Portable Version:
echo   Location: dist\SQLServerPipeline\
echo   Main EXE: dist\SQLServerPipeline\SQLServerPipeline.exe
echo.

if exist "dist\installer\SQLServerPipeline_v2.2.0_Setup.exe" (
    echo Installer Version:
    echo   Location: dist\installer\
    echo   Installer: dist\installer\SQLServerPipeline_v2.2.0_Setup.exe
    echo.
)

echo ========================================
echo Next Steps
echo ========================================
echo.
echo 1. Test the portable version in dist\SQLServerPipeline\
echo 2. Test the installer from dist\installer\
echo 3. Distribute to users
echo.
echo For portable version:
echo   - Zip the dist\SQLServerPipeline\ folder
echo   - Users extract and run SQLServerPipeline.exe
echo.
echo For installer version:
echo   - Share the .exe file from dist\installer\
echo   - Users run the installer
echo   - Program appears in Programs and Features
echo.

pause
