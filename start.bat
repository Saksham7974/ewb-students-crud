@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo *** .venv nahi mili. Pehle 'setup.bat' chalao. ***
    pause
    exit /b 1
)

echo ============================================
echo   Server start ho raha hai...
echo   Browser me kholo:  http://localhost:8000/docs
echo   Band karne ke liye: is window me Ctrl+C
echo ============================================
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload

pause
