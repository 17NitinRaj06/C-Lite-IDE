@echo off
rem =====================================================================
rem  C-Lite IDE - build pipeline
rem
rem  1. Compiles packaging\app.rc with the bundled MinGW windres into
rem     build\app.res (proves the icon/version resource pipeline works).
rem  2. Builds "C-Lite IDE.exe" with PyInstaller, embedding the feather
rem     icon (icons\app.ico) directly into the executable so the taskbar,
rem     Alt+Tab, the .exe icon in Explorer and any shortcuts show it.
rem  3. Copies the runtime dependencies (bundled MinGW compiler, headers,
rem     BGI runtime, examples, icons) next to the exe so the packaged app
rem     is self-contained and fully offline.
rem
rem  Output: dist\C-Lite IDE\C-Lite IDE.exe
rem
rem  Notes: windres needs a PATH with the toolchain's gcc (its default
rem  preprocessor) and forward-slash input paths -- this binutils build
rem  mangles backslash paths in gcc -E line markers.
rem =====================================================================
setlocal
cd /d "%~dp0.."

set PY=python
set TOOLCHAIN=compiler\mingw\bin
set WINDRES=compiler\mingw\bin\windres.exe
set OUT=dist\C-Lite IDE

if not exist "%WINDRES%" (
    echo ERROR: bundled windres not found: %WINDRES%
    exit /b 1
)
set "PATH=%CD%\%TOOLCHAIN%;%PATH%"

rem Read version from version.txt
set VERSION=
for /f "usebackq delims=" %%a in (`type version.txt`) do set VERSION=%%a
if "%VERSION%"=="" (
    echo ERROR: Could not read version from version.txt
    exit /b 1
)
echo Version: %VERSION%

rem Parse version components for FILEVERSION (major,minor,patch,build)
for /f "tokens=1-3 delims=." %%a in ("%VERSION%") do (
    set VER_MAJOR=%%a
    set VER_MINOR=%%b
    set VER_PATCH=%%c
)
set VER_BUILD=0

rem Generate app.rc with version
echo Generating packaging\app.rc with version %VERSION%...
(
    echo IDI_APP ICON "../icons/app.ico"
    echo.
    echo VS_VERSION_INFO VERSIONINFO
    echo  FILEVERSION %VER_MAJOR%,%VER_MINOR%,%VER_PATCH%,%VER_BUILD%
    echo  PRODUCTVERSION %VER_MAJOR%,%VER_MINOR%,%VER_PATCH%,%VER_BUILD%
    echo  FILEFLAGSMASK 0x3fL
    echo  FILEFLAGS 0x0L
    echo  FILEOS 0x40004L
    echo  FILETYPE 0x1L
    echo  FILESUBTYPE 0x0L
    echo BEGIN
    echo     BLOCK "StringFileInfo"
    echo     BEGIN
    echo         BLOCK "040904b0"
    echo         BEGIN
    echo             VALUE "CompanyName", "C-Lite"
    echo             VALUE "FileDescription", "C-Lite IDE - Turbo C compatible IDE for C/C++ students"
    echo             VALUE "FileVersion", "%VERSION%"
    echo             VALUE "InternalName", "C-Lite IDE"
    echo             VALUE "OriginalFilename", "C-Lite IDE.exe"
    echo             VALUE "ProductName", "C-Lite IDE"
    echo             VALUE "ProductVersion", "%VERSION%"
    echo         END
    echo     END
    echo     BLOCK "VarFileInfo"
    echo     BEGIN
    echo         VALUE "Translation", 0x409, 1200
    echo     END
    echo END
) > packaging\app.rc

rem Generate version_info.txt for PyInstaller (text-based version info)
echo Generating build\version_info.txt for PyInstaller...
%PY% packaging\gen_version_info.py
if errorlevel 1 (
    echo ERROR: Failed to generate version_info.txt
    exit /b 1
)

rem Clean previous dist output to ensure fresh build
echo Cleaning previous dist output...
if exist "%OUT%" rmdir /s /q "%OUT%" 2>nul

echo === [1/3] windres: compiling packaging\app.rc ==="
"%WINDRES%" --preprocessor="gcc -E -xc -DRC_INVOKED" ^
    "packaging/app.rc" -O coff -o "build\app.res"
if errorlevel 1 (
    echo windres FAILED
    exit /b 1
)
echo     ^-^> build\app.res

echo === [2/3] PyInstaller: building "C-Lite IDE.exe" ==="
%PY% -m PyInstaller --noconfirm --clean --onedir --windowed ^
    --name "C-Lite IDE" ^
    --icon "icons\app.ico" ^
    --add-data "icons;icons" ^
    --version-file "build\version_info.txt" ^
    clite.py
if errorlevel 1 (
    echo PyInstaller FAILED
    exit /b 1
)

echo === [3/3] copying runtime dependencies next to the exe ==="
xcopy /e /i /y compiler "%OUT%\compiler" >nul
xcopy /e /i /y include  "%OUT%\include"  >nul
xcopy /e /i /y runtime  "%OUT%\runtime"  >nul
xcopy /e /i /y examples "%OUT%\examples" >nul
if not exist "%OUT%\icons\app.ico" xcopy /e /i /y icons "%OUT%\icons" >nul
copy /y version.txt "%OUT%\version.txt" >nul

echo.
echo === Done ===
echo Executable: %cd%\%OUT%\C-Lite IDE.exe
endlocal