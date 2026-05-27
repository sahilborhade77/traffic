@echo off
TITLE Traffic Intelligence System - Unified Launcher
echo ======================================================
echo 🚦 STARTING TRAFFIC INTELLIGENCE SYSTEM 🚦
echo ======================================================

:: 1. Setup Environment
echo [1/4] Activating Virtual Environment...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found.
)

echo [1.5/4] Checking Dependencies...
python -m pip install gymnasium==0.29.1 stable-baselines3==2.2.1 lapx==0.9.4 --quiet

echo [1.6/4] Stopping old project processes...
taskkill /FI "WINDOWTITLE eq Traffic-API*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Traffic-Vision-Pipeline*" /T /F >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter 'name = ''python.exe'' or name = ''streamlit.exe''' | Where-Object { $_.CommandLine -match 'uvicorn src.dashboard.api:app|main_pipeline.py|streamlit run src/dashboard/app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
timeout /t 2 > nul

:: 2. Start API
echo [2/4] Starting API Server (Uvicorn)...
start "Traffic-API" cmd /k "python -m uvicorn src.dashboard.api:app --host 0.0.0.0 --port 8000"
timeout /t 3 > nul

:: 3. Start Processing Pipeline
echo [3/4] Starting Vision Processing Pipeline...
start "Traffic-Vision-Pipeline" cmd /k "python main_pipeline.py"
timeout /t 5 > nul

:: 4. Start Dashboard
echo [4/4] Launching Enhanced Dashboard (Streamlit)...
python -m streamlit run src/dashboard/app_enhanced.py --server.port 8501

echo ======================================================
echo System initialized. Press any key to stop all processes.
echo (Close the individual windows to stop specific modules)
echo ======================================================
pause
