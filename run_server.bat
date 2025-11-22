@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src

echo ===================================================
echo   Deep Research Agent Backend
echo ===================================================
echo.

:: Try to activate virtual environment
if exist "..\.venv\Scripts\activate.bat" (
    echo Activating virtual environment from ..\.venv
    call "..\.venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment from .venv
    call ".venv\Scripts\activate.bat"
) else (
    echo No virtual environment found. Using system Python.
)

echo.
echo Starting Uvicorn server...
echo Open your browser at: http://localhost:8000
echo.

:: Check if uvicorn is installed
python -c "import uvicorn" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Error: uvicorn is not installed.
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

python -m uvicorn deep_research_agent.app:app --host 0.0.0.0 --port 8000 --reload
pause
