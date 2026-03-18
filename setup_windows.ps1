$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=========================================="
Write-Host "  APS 모니터링 - Windows 설치 스크립트"
Write-Host "=========================================="
Write-Host ""

function Get-PythonCmd {
    if (Test-Path ".venv\Scripts\python.exe") { return ".venv\Scripts\python.exe" }
    if (Test-Path "venv\Scripts\python.exe") { return "venv\Scripts\python.exe" }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return "py" }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return "python" }
    return $null
}

$pythonCmd = Get-PythonCmd
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python/py를 찾을 수 없습니다."
    Write-Host "Python 3.10+ 설치 후 다시 실행해 주세요. (python.org 권장)"
    exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe") -and -not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "가상환경(.venv) 생성 중..."
    & $pythonCmd -m venv .venv
    $pythonCmd = ".venv\Scripts\python.exe"
}

Write-Host "pip 업그레이드/의존성 설치 중..."
& $pythonCmd -m ensurepip --default-pip | Out-Null
& $pythonCmd -m pip install --upgrade pip
& $pythonCmd -m pip install -r requirements.txt

Write-Host ""
Write-Host "Playwright Chromium 설치 중..."
& $pythonCmd -m playwright install chromium

Write-Host ""
Write-Host "완료."
Write-Host "- 웹앱 실행: run_app.bat (또는 .\\run_server.ps1)"
Write-Host "- 모니터링(콘솔) 실행: run_monitor.bat"

