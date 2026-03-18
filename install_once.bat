@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ==========================================
echo   APS 모니터링 - 처음 한 번만 설치
echo ==========================================
echo.
echo 가상환경, 패키지, Playwright 브라우저를 설치합니다.
echo 완료 후에는 run_app.bat 만 더블클릭해서 사용하세요.
echo.

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& \"%~dp0setup_windows.ps1\""
if %errorlevel% neq 0 (
    echo.
    echo [오류] 설치 중 문제가 발생했습니다.
    echo - Python 3.10 이상이 설치되어 있는지 확인하세요. (python.org)
    echo - "Add Python to PATH" 옵션으로 설치했는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   설치 완료.
echo   이제 run_app.bat 을 더블클릭해서 실행하세요.
echo ==========================================
pause
