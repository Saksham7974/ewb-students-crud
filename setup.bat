@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   EWB Students CRUD - SETUP
echo ============================================
echo.

echo [1/5] Python check...
python --version
if errorlevel 1 goto :pyerror

echo.
echo [2/5] Virtual environment bana rahe hain...
python -m venv .venv
if errorlevel 1 goto :venverror

echo.
echo [3/5] Dependencies install ho rahi hain (fastapi, uvicorn, pydantic, httpx, pytest)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :piperror

echo.
echo [4/5] Dummy data daal rahe hain...
".venv\Scripts\python.exe" seed.py

echo.
echo [5/5] Tests chala rahe hain...
".venv\Scripts\python.exe" -m pytest -v

echo.
echo ============================================
echo   SETUP DONE. Ab 'start.bat' chalao server ke liye.
echo ============================================
pause
exit /b 0

:pyerror
echo.
echo *** ERROR: 'python' nahi mila. ***
echo Python install karo: https://www.python.org/downloads/
echo Install karte time "Add python.exe to PATH" wala box TICK karna zaroori hai.
pause
exit /b 1

:venverror
echo.
echo *** ERROR: virtual environment nahi bani. Upar ka message mujhe bhejo. ***
pause
exit /b 1

:piperror
echo.
echo *** ERROR: install fail hua. Internet on hai? Upar ka message mujhe bhejo. ***
pause
exit /b 1
