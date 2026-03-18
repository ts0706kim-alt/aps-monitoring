# APS 모니터링 - 데일리 작업 등록 해제

param([string]$TaskName = "APS-Monitoring-Daily")

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "등록된 작업이 없습니다: $TaskName"
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "작업 제거됨: $TaskName"
