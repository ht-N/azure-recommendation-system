@echo off
echo ========================================
echo    AI Recommendation System Demo
echo ========================================
echo.

REM Check for --force argument
if "%1"=="--force" (
    echo ⚡ FORCE UPDATE MODE - Will bypass recent recommendations check
    echo    Perfect for testing and demonstrations!
    echo.
    set FORCE_FLAG=--force
) else (
    echo 💡 Tip: Use 'start_demo.bat --force' to bypass recent recommendations check
    echo.
    set FORCE_FLAG=
)

REM Change to demo directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo Starting demo...
echo Demo will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

REM Run the demo with force flag if specified
python run_demo.py %FORCE_FLAG%

pause
