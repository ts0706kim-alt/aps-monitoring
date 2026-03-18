@echo off
setlocal
cd /d "%~dp0"

REM 가상환경이 있으면 우선 사용
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "playwright_monitor.py"
  goto :end
)
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" "playwright_monitor.py"
  goto :end
)

REM 없으면 시스템 Python/py 사용
where py >nul 2>nul
if %errorlevel%==0 (
  py "playwright_monitor.py"
  goto :end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python "playwright_monitor.py"
  goto :end
)

echo [ERROR] Python/py를 찾을 수 없습니다.
echo - python.org의 Python 3.10+ 설치 후 다시 실행하세요.

:end
pause

