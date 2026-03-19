@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

REM 로그 폴더 생성 후 매 실행마다 로그 저장
if not exist "logs" mkdir logs
set LOG=logs\monitor_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log
set LOG=%LOG: =0%

REM 가상환경이 있으면 우선 사용
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run_daily_with_email.py >> "%LOG%" 2>&1
  exit /b %errorlevel%
)
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" run_daily_with_email.py >> "%LOG%" 2>&1
  exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
  py run_daily_with_email.py >> "%LOG%" 2>&1
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python run_daily_with_email.py >> "%LOG%" 2>&1
  exit /b %errorlevel%
)

echo [ERROR] Python/py를 찾을 수 없습니다. >> "%LOG%" 2>&1
exit /b 1
