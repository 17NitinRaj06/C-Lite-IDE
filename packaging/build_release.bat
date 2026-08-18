@echo off
rem =====================================================================
rem  C-Lite IDE - Release Build Script
rem
rem  This script builds a complete release installer:
rem  1. Reads version from version.txt
rem  2. Cleans previous build output
rem  3. Builds C-Lite IDE executable (via build_ide.bat)
rem  4. Generates Inno Setup script with version
rem  5. Compiles installer with Inno Setup
rem  6. Outputs to release\C-Lite-IDE-Setup-<version>.exe
rem
rem  Usage: packaging\build_release.bat
rem =====================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

rem ---------------------------------------------------------------------
rem  Configuration
rem ---------------------------------------------------------------------
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo ERROR: Inno Setup compiler (ISCC.exe) not found.
    echo Please install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    exit /b 1
)

rem ---------------------------------------------------------------------
rem  Read version
rem ---------------------------------------------------------------------
set VERSION=
for /f "usebackq delims=" %%a in (`type version.txt`) do set VERSION=%%a
if "%VERSION%"=="" (
    echo ERROR: Could not read version from version.txt
    exit /b 1
)
echo =====================================================================
echo Building C-Lite IDE v%VERSION%
echo =====================================================================

rem ---------------------------------------------------------------------
rem  Clean previous build output
rem ---------------------------------------------------------------------
echo.
echo [1/5] Cleaning previous build output...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist release rmdir /s /q release 2>nul
mkdir release 2>nul

rem ---------------------------------------------------------------------
rem  Build C-Lite IDE executable
rem ---------------------------------------------------------------------
echo.
echo [2/5] Building C-Lite IDE executable...
call packaging\build_ide.bat
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

rem ---------------------------------------------------------------------
rem  Verify build output
rem ---------------------------------------------------------------------
echo.
echo [3/5] Verifying build output...
set EXE_PATH=dist\C-Lite IDE\C-Lite IDE.exe
if not exist "%EXE_PATH%" (
    echo ERROR: Executable not found at %EXE_PATH%
    exit /b 1
)
echo Executable found: %EXE_PATH%

rem Verify required directories exist
for %%d in (compiler include runtime examples icons) do (
    if not exist "dist\C-Lite IDE\%%d" (
        echo ERROR: Required directory '%%d' not found in build output
        exit /b 1
    )
)

rem ---------------------------------------------------------------------
rem  Generate Inno Setup script with version
rem ---------------------------------------------------------------------
echo.
echo [4/5] Generating Inno Setup script...
set ISS_TEMPLATE=packaging\C-Lite-IDE.iss
set ISS_GENERATED=packaging\C-Lite-IDE-generated.iss

if not exist "%ISS_TEMPLATE%" (
    echo ERROR: Inno Setup template not found: %ISS_TEMPLATE%
    exit /b 1
)

rem Replace VERSION_PLACEHOLDER with actual version
powershell -Command "(Get-Content '%ISS_TEMPLATE%') -replace 'VERSION_PLACEHOLDER', '%VERSION%' | Set-Content '%ISS_GENERATED%' -Encoding UTF8"
if errorlevel 1 (
    echo ERROR: Failed to generate Inno Setup script
    exit /b 1
)
echo Generated: %ISS_GENERATED%

rem ---------------------------------------------------------------------
rem  Compile installer with Inno Setup
rem ---------------------------------------------------------------------
echo.
echo [5/5] Compiling installer with Inno Setup...
%ISCC% "%ISS_GENERATED%"
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed
    exit /b 1
)

rem ---------------------------------------------------------------------
rem  Verify installer output
rem ---------------------------------------------------------------------
set INSTALLER=release\C-Lite-IDE-Setup-%VERSION%.exe
if not exist "%INSTALLER%" (
    echo ERROR: Installer not found at %INSTALLER%
    exit /b 1
)

echo.
echo =====================================================================
echo BUILD SUCCESSFUL
echo =====================================================================
echo Version: %VERSION%
echo Installer: %cd%\%INSTALLER%
echo.
echo To create a GitHub release:
echo   1. git tag v%VERSION%
echo   2. git push origin v%VERSION%
echo   3. Create release on GitHub and upload %INSTALLER%
echo =====================================================================

endlocal