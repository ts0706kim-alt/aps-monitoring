# APS 모니터링 웹 서버 실행
Set-Location $PSScriptRoot

Write-Host "=========================================="
Write-Host "  APS 모니터링 웹 서버"
Write-Host "  브라우저에서 http://127.0.0.1:5000 접속"
Write-Host "=========================================="
Write-Host ""

# venv가 있으면 venv의 Python으로 실행 (권장)
if (Test-Path "venv\Scripts\python.exe") {
    & "venv\Scripts\python.exe" app.py
    exit $LASTEXITCODE
}
if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" app.py
    exit $LASTEXITCODE
}

# 가상환경 활성화 후 시도
if (Test-Path "venv\Scripts\Activate.ps1") { & "venv\Scripts\Activate.ps1" }
elseif (Test-Path ".venv\Scripts\Activate.ps1") { & ".venv\Scripts\Activate.ps1" }
try {
    python app.py
} catch {
    py app.py
}
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[오류] app.py를 실행할 수 없습니다."
    Write-Host "  pip install -r requirements.txt 후 다시 시도하세요."
    Read-Host "Enter 키를 누르면 종료"
}
