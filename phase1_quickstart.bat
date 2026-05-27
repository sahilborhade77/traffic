@echo off
REM ============================================================================
REM Phase 1: Quick Start Script for Windows
REM Smart AI Traffic Intelligence System
REM ============================================================================

setlocal enabledelayedexpansion

REM Colors for output
set GREEN=[92m
set RED=[91m
set YELLOW=[93m
set BLUE=[94m
set RESET=[0m

echo.
echo %BLUE%============================================================================
echo   PHASE 1: Smart AI Traffic Intelligence System - Quick Start
echo ============================================================================%RESET%
echo.

REM Check if .env exists
if not exist ".env" (
    echo %RED%ERROR: .env file not found in project root%RESET%
    echo Please create .env file first
    pause
    exit /b 1
)

echo %GREEN%[✓] .env file found%RESET%

REM Check if venv exists
if not exist ".venv" (
    echo %YELLOW%[!] Virtual environment not found, creating...%RESET%
    python -m venv .venv
    if errorlevel 1 (
        echo %RED%ERROR: Failed to create virtual environment%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%[✓] Virtual environment created%RESET%
)

REM Activate venv
echo.
echo %BLUE%Activating virtual environment...%RESET%
call .venv\Scripts\activate.bat

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%ERROR: Python not found in virtual environment%RESET%
    pause
    exit /b 1
)
echo %GREEN%[✓] Python activated%RESET%

REM Menu
:menu
echo.
echo %BLUE%========================================%RESET%
echo %BLUE%  Phase 1 Startup Options%RESET%
echo %BLUE%========================================%RESET%
echo.
echo 1. Start Backend (FastAPI only)
echo 2. Start Dashboard (Streamlit only)
echo 3. Run Detection/Tracking Tests
echo 4. View Execution Guide
echo 5. Full startup info
echo 6. Exit
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto backend
if "%choice%"=="2" goto dashboard
if "%choice%"=="3" goto tests
if "%choice%"=="4" goto guide
if "%choice%"=="5" goto info
if "%choice%"=="6" goto exit
echo %RED%Invalid choice%RESET%
goto menu

:backend
echo.
echo %BLUE%Starting FastAPI Backend...%RESET%
echo %YELLOW%Keep this window open - do not close!%RESET%
echo %YELLOW%Open another terminal for dashboard (option 2)%RESET%
echo.
python -m uvicorn src.api.main_api:app --reload --host 0.0.0.0 --port 8000
goto end

:dashboard
echo.
echo %BLUE%Starting Streamlit Dashboard...%RESET%
echo %YELLOW%Keep this window open - do not close!%RESET%
echo %YELLOW%Make sure backend is running in another terminal!%RESET%
echo.
python -m streamlit run src\dashboard\app.py
goto end

:tests
echo.
echo %BLUE%Running Detection & Tracking Tests...%RESET%
echo.
python phase1_test_detection_tracking.py
echo.
pause
goto menu

:guide
echo.
start "" "PHASE1_EXECUTION_GUIDE.md"
timeout /t 2
goto menu

:info
echo.
echo %BLUE%========================================%RESET%
echo %BLUE%  Phase 1 Information%RESET%
echo %BLUE%========================================%RESET%
echo.
echo 📋 Project: Smart AI Traffic Intelligence System
echo 🔄 Phase: 1 (Critical Fixes)
echo 📅 Duration: 1-2 weeks
echo 🎯 Status: STARTING NOW
echo.
echo 📌 Key URLs:
echo   - Dashboard: http://localhost:8501
echo   - API: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.
echo 📋 Quick Reference:
echo   - Backend port: 8000
echo   - Dashboard port: 8501
echo   - Database: sqlite:///traffic.db
echo.
echo 🚀 Next Steps After Phase 1:
echo   1. Verify all services running
echo   2. Run test suite (option 3)
echo   3. Access dashboard (option 2)
echo   4. Check API docs
echo   5. Proceed to Phase 2
echo.
pause
goto menu

:end
pause
endlocal
