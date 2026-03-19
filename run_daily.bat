@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 가상환경이 있다면 활성화 (venv 또는 .venv)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python run_daily_with_email.py
pause
