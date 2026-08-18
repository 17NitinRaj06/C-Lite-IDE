@echo off
rem C-Lite IDE launcher
cd /d "%~dp0"
where python >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw clite.py 2>nul
    if %errorlevel%==0 exit /b 0
)
python clite.py
if %errorlevel% neq 0 pause