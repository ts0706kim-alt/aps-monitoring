# APS 모니터링 - Windows 작업 스케줄러에 데일리 실행 등록
# 관리자 권한 불필요 (현재 사용자 작업으로 등록)

param(
    [string]$Time = "09:00",   # 매일 실행 시각 (HH:mm, 24시간)
    [string]$TaskName = "APS-Monitoring-Daily"
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$BatPath = Join-Path $ProjectDir "run_monitor_scheduled.bat"

if (-not (Test-Path $BatPath)) {
    Write-Error "run_monitor_scheduled.bat을 찾을 수 없습니다: $BatPath"
}

# 기존 같은 이름 작업 삭제
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 작업 '$TaskName' 제거됨."
}

$Action = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings | Out-Null

Write-Host ""
Write-Host "등록 완료: 매일 $Time 에 '$TaskName' 실행"
Write-Host "- 확인: 작업 스케줄러( taskschd.msc ) 에서 '$TaskName' 검색"
Write-Host "- 제거: .\unregister_daily_task.ps1"
Write-Host ""
