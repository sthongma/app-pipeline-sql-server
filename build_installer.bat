@echo off
echo ======================================
echo Building SQL Server Pipeline Installer
echo ======================================
echo.

echo Step 1: Building executable with PyInstaller...
echo ------------------------------------------------
pyinstaller SQLServerPipeline.spec --clean
if errorlevel 1 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Creating installer with Inno Setup...
echo ------------------------------------------------
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_resources\installer_script.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" build_resources\installer_script.iss
) else (
    echo WARNING: Inno Setup not found!
    echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
    echo Or run ISCC.exe manually on build_resources\installer_script.iss
    pause
    exit /b 1
)

echo.
echo ======================================
echo Build Complete!
echo ======================================
echo Installer output: installer_output\SQLServerPipeline_v1.0.0_Setup.exe
echo.
pause
