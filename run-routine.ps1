# paper-monitor 주간 무인 루틴 런처 (Windows Task Scheduler에서 호출)
# 로컬 데이터(D: DB, OneDrive vault)에 접근해야 하므로 이 PC에서 실행한다.
# 등록 예:
#   schtasks /Create /TN "PaperMonitor Weekly" /SC WEEKLY /D MON /ST 08:00 /F ^
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\230016\OneDrive\claude\paper-monitor\run-routine.ps1\""

# 네이티브 파이썬/CLI의 stderr(진행바·경고)에 런처가 중단되지 않도록 Continue
$ErrorActionPreference = 'Continue'
$repo   = 'C:\Users\230016\OneDrive\claude\paper-monitor'
$logdir = 'D:\dev\paper-monitor-data\routine-logs'   # OneDrive 밖(동기화 충돌 방지)
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
$log = Join-Path $logdir ("routine_{0}.log" -f (Get-Date -Format 'yyyy-MM-dd_HHmmss'))

Set-Location $repo

# claude CLI 경로 확인 (Task Scheduler는 축소된 PATH로 실행될 수 있음)
$claude = (Get-Command claude -ErrorAction SilentlyContinue).Source
if (-not $claude) {
    # 네이티브 설치 기본 경로 폴백
    $fallback = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
    if (Test-Path $fallback) { $claude = $fallback }
}
if (-not $claude) {
    "[{0}] claude CLI를 찾지 못함. 설치 후 PATH 또는 이 스크립트의 경로를 확인하세요." -f (Get-Date) | Out-File -FilePath $log -Encoding utf8
    exit 1
}

"[{0}] routine 시작 (claude: {1})" -f (Get-Date), $claude | Out-File -FilePath $log -Encoding utf8

# === 1단계: 신규 fetch (순수 파이썬, 키워드별 rate-limit으로 수 분 소요) ===
# claude 도구 타임아웃/백그라운드 제약을 피하려 claude 밖에서 직접 실행한다.
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path $py) {
    "[{0}] fetch_new 시작" -f (Get-Date) | Out-File -FilePath $log -Append -Encoding utf8
    $null | & $py scripts\fetch_new.py 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
    "[{0}] fetch_new 종료 (exit={1})" -f (Get-Date), $LASTEXITCODE | Out-File -FilePath $log -Append -Encoding utf8
} else {
    "[{0}] venv python 없음 ({1}) — fetch 스킵" -f (Get-Date), $py | Out-File -FilePath $log -Append -Encoding utf8
}

# === 2단계: 큐레이션(triage→한글요약→인덱스)은 claude /routine이 수행 ===
# 무인 실행: 권한 프롬프트로 멈추지 않도록 함. (개인 로컬 자동화 — 신뢰 환경)
# 더 좁히려면: --permission-mode dontAsk --allowedTools "Bash,Read,Write,Edit"
# $null 파이프로 stdin을 즉시 닫아 "no stdin data" 3초 대기 회피
$null | & $claude -p "/routine" --dangerously-skip-permissions 2>&1 |
    Out-File -FilePath $log -Append -Encoding utf8

"[{0}] routine 종료 (exit={1})" -f (Get-Date), $LASTEXITCODE | Out-File -FilePath $log -Append -Encoding utf8
