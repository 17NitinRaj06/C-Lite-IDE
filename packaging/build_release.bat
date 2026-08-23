@echo off
rem =====================================================================
rem  C-Lite IDE - Release Build Script (NSIS-based)
rem
rem  This script builds a complete release installer using NSIS:
rem  1. Reads version from version.txt
rem  2. Cleans previous build output (build, dist, release)
rem  3. Builds C-Lite IDE executable (via build_ide.bat)
rem  4. Verifies build output
rem  5. Generates NSIS script with version substitution
rem  6. Compiles installer with NSIS (makensis)
rem  7. Outputs to release\C-Lite-IDE-Setup-<version>.exe
rem
rem  Usage: packaging\build_release.bat
rem =====================================================================
setlocal enabledelayedexpansion

cd /d "%~dp0.."

rem ---------------------------------------------------------------------
rem  Configuration
rem ---------------------------------------------------------------------
rem Find makensis (NSIS compiler)
set MAKENSIS=
where makensis >nul 2>&1
if not errorlevel 1 (
    set MAKENSIS=makensis
) else (
    rem Try common NSIS install locations
    if exist "C:\Program Files (x86)\NSIS\Bin\makensis.exe" set MAKENSIS="C:\Program Files (x86)\NSIS\Bin\makensis.exe"
    if exist "C:\Program Files\NSIS\Bin\makensis.exe" set MAKENSIS="C:\Program Files\NSIS\Bin\makensis.exe"
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" set MAKENSIS="C:\Program Files (x86)\NSIS\makensis.exe"
    if exist "C:\Program Files\NSIS\makensis.exe" set MAKENSIS="C:\Program Files\NSIS\makensis.exe"
    if exist "%LOCALAPPDATA%\Programs\NSIS\makensis.exe" set MAKENSIS="%LOCALAPPDATA%\Programs\NSIS\makensis.exe"
    if exist "C:\Temp\nsis\nsis-3.12\Bin\makensis.exe" set MAKENSIS="C:\Temp\nsis\nsis-3.12\Bin\makensis.exe"
)
if "%MAKENSIS%"=="" (
    echo ERROR: NSIS compiler (makensis.exe) not found.
    echo Please install NSIS 3 from https://nsis.sourceforge.io/Download
    exit /b 1
)
echo Using NSIS compiler: %MAKENSIS%

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
echo [1/6] Cleaning previous build output...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist release rmdir /s /q release 2>nul
mkdir release 2>nul

rem ---------------------------------------------------------------------
rem  Build C-Lite IDE executable
rem ---------------------------------------------------------------------
echo.
echo [2/6] Building C-Lite IDE executable...
call packaging\build_ide.bat
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

rem ---------------------------------------------------------------------
rem  Verify build output
rem ---------------------------------------------------------------------
echo.
echo [3/6] Verifying build output...
set EXE_PATH=dist\C-Lite IDE\C-Lite IDE.exe
if not exist "%EXE_PATH%" (
    echo ERROR: Executable not found at %EXE_PATH%
    exit /b 1
)
echo Executable found: %EXE_PATH%

rem Get executable timestamp
for %%f in ("%EXE_PATH%") do set EXE_TIME=%%~tf
echo Executable timestamp: %EXE_TIME%

rem Verify required directories exist
for %%d in (compiler include runtime examples icons) do (
    if not exist "dist\C-Lite IDE\%%d" (
        echo ERROR: Required directory '%%d' not found in build output
        exit /b 1
    )
)

rem ---------------------------------------------------------------------
rem  Generate NSIS script with version substitution
rem ---------------------------------------------------------------------
echo.
echo [4/6] Generating NSIS script with version %VERSION%...
set NSI_TEMPLATE=packaging\C-Lite-IDE.nsi
set NSI_GENERATED=packaging\C-Lite-IDE-generated.nsi

if not exist "%NSI_TEMPLATE%" (
    echo ERROR: NSIS template not found: %NSI_TEMPLATE%
    exit /b 1
)

rem Replace APP_VERSION and APP_VERSION in the NSIS script
powershell -Command "(Get-Content '%NSI_TEMPLATE%') -replace '!define APP_VERSION \"1\.0\.0\"', '!define APP_VERSION \"%VERSION%\"' | Set-Content '%NSI_GENERATED%' -Encoding UTF8"
if errorlevel 1 (
    echo ERROR: Failed to generate NSIS script
    exit /b 1
)
echo Generated: %NSI_GENERATED%

rem ---------------------------------------------------------------------
rem  Compile installer with NSIS
rem ---------------------------------------------------------------------
echo.
echo [5/6] Compiling installer with NSIS...
%MAKENSIS% "%NSI_GENERATED%"
if errorlevel 1 (
    echo ERROR: NSIS compilation failed
    exit /b 1
)

rem ---------------------------------------------------------------------
rem  Verify installer output
rem ---------------------------------------------------------------------
echo.
echo [6/6] Verifying installer output...
set INSTALLER=release\C-Lite-IDE-Setup-%VERSION%.exe
if not exist "%INSTALLER%" (
    echo ERROR: Installer not found at %INSTALLER%
    exit /b 1
)

for %%f in ("%INSTALLER%") do set INSTALLER_SIZE=%%~zf
for %%f in ("%INSTALLER%") do set INSTALLER_TIME=%%~tf

echo.
echo =====================================================================
echo BUILD SUCCESSFUL
echo =====================================================================
echo Version: %VERSION%
echo Executable: %cd%\dist\C-Lite IDE\C-Lite IDE.exe
echo Installer: %cd%\release\C-Lite-IDE-Setup-%VERSION%.exe
echo Installer size: %INSTALLER_SIZE% bytes
echo Installer timestamp: %INSTALLER_TIME%
echo.
echo To create a GitHub release:
echo   1. git tag v%VERSION%
echo   2. git push origin v%VERSION%
echo   3. Create release on GitHub and upload release\C-Lite-IDE-Setup-%VERSION%.exe
echo =====================================================================

endlocal