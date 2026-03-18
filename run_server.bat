@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   APS 모니터링 웹 서버
echo   브라우저에서 http://127.0.0.1:5000 접속
echo ==========================================
echo.

REM venv가 있으면 venv의 Python으로 실행 (권장)
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" app.py
    goto :done
)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
    goto :done
)

REM 가상환경 없으면 시스템 Python
call venv\Scripts\activate.bat 2>nul
call .venv\Scripts\activate.bat 2>nul
python app.py 2>nul
if errorlevel 1 py app.py 2>nul
if errorlevel 1 (
    echo.
    echo [오류] Python으로 app.py를 실행할 수 없습니다.
    echo 다음을 확인하세요:
    echo   1. Python 설치: https://www.python.org/downloads/
    echo   2. 프로젝트 폴더에서: pip install -r requirements.txt
    echo   3. 가상환경 사용 시: venv\Scripts\python.exe app.py
    pause
)
:done
