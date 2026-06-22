# =============================================================================
# paper-monitor Windows Setup Script  (v3)
#   v2 변경사항 + pip-system-certs 설치 (사내망 SSL inspection 대응)
#
# Run: powershell -ExecutionPolicy Bypass -File .\setup.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

$ProjectPath = "C:\Users\230016\OneDrive\claude\paper-monitor"
$PythonId    = "Python.Python.3.12"

function Write-Step($msg)  { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)    { Write-Host "    [OK] $msg"   -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }

function Get-PythonCmd {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $out = & py -3 --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$out" -match "Python 3\.") {
            return @{ Exe = "py"; Args = @("-3") }
        }
    }
    $candidates = @(Get-Command python -All -ErrorAction SilentlyContinue)
    foreach ($c in $candidates) {
        if ($c.Source -like "*WindowsApps*") { continue }
        $out = & $c.Source --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$out" -match "Python 3\.") {
            return @{ Exe = $c.Source; Args = @() }
        }
    }
    return $null
}

# ---- 1. winget ---------------------------------------------------------------
Write-Step "Checking winget"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not found. Install 'App Installer' from Microsoft Store."
    exit 1
}
Write-OK "winget found"

# ---- 2. Python ---------------------------------------------------------------
Write-Step "Locating Python 3"
$py = Get-PythonCmd
if ($py) {
    $ver = & $py.Exe @($py.Args) --version 2>&1
    Write-OK "Using: $($py.Exe) $($py.Args -join ' ')  ($ver)"
} else {
    Write-Host "    Python 3 not found. Installing via winget..."
    & winget install --id $PythonId -e --source winget `
        --accept-package-agreements --accept-source-agreements `
        --scope user
    $wingetExit = $LASTEXITCODE
    Write-Host "    (winget exited with $wingetExit - this can be benign)"

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")

    $py = Get-PythonCmd
    if (-not $py) {
        Write-Error "No working Python 3 detected. Open a NEW PowerShell window and re-run, or disable the Store stub: Settings -> Apps -> App execution aliases -> python.exe / python3.exe OFF."
        exit 1
    }
    Write-OK "Detected after install: $($py.Exe) $($py.Args -join ' ')"
}

# ---- 3. Project dir ----------------------------------------------------------
Write-Step "Entering project directory"
if (-not (Test-Path $ProjectPath)) {
    Write-Error "Project path not found: $ProjectPath"
    exit 1
}
Set-Location $ProjectPath
Write-OK "CWD = $ProjectPath"

# ---- 4. venv -----------------------------------------------------------------
Write-Step "Creating .venv"
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-OK ".venv exists, skipping"
} else {
    & $py.Exe @($py.Args) -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Error "venv creation failed."; exit 1 }
    Write-OK ".venv created"
}

$VenvPy = (Resolve-Path ".\.venv\Scripts\python.exe").Path
Write-OK "venv python: $VenvPy"

# ---- 5. pip + corporate SSL fix + deps ---------------------------------------
Write-Step "Upgrading pip"
& $VenvPy -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Write-Error "pip upgrade failed."; exit 1 }

Write-Step "Installing pip-system-certs (use Windows cert store for requests/urllib3)"
# pip-system-certs adds a .pth file that monkey-patches requests/urllib3 on
# Python startup to trust the Windows certificate store. Fixes SSL errors
# behind corporate proxies that do TLS inspection (Zscaler, Palo Alto, etc.).
& $VenvPy -m pip install pip-system-certs
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "pip-system-certs install failed. If you hit SSL errors later, see the troubleshooting block at the bottom of this script."
} else {
    Write-OK "pip-system-certs installed"
}

Write-Step "Installing requirements.txt"
if (Test-Path ".\requirements.txt") {
    & $VenvPy -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed."; exit 1 }
    Write-OK "Dependencies installed"
} else {
    Write-Warn2 "requirements.txt not found"
}

# ---- 6. backfill -------------------------------------------------------------
Write-Step "Running scripts/backfill.py"
if (-not (Test-Path ".\scripts\backfill.py")) {
    Write-Error "scripts\backfill.py not found"
    exit 1
}

$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"

& $VenvPy .\scripts\backfill.py
$rc = $LASTEXITCODE
if ($rc -eq 0) {
    Write-OK "backfill.py finished"
} else {
    Write-Error "backfill.py exited with code $rc"
    exit $rc
}

Write-Host "`nAll done." -ForegroundColor Green

# =============================================================================
# Troubleshooting: SSL errors persist even after pip-system-certs
# -----------------------------------------------------------------------------
# Plan B - Export corporate CA from Windows and point requests at it manually:
#
#   1) certmgr.msc 열기 -> 신뢰할 수 있는 루트 인증 기관 -> Certificates
#      -> 회사 CA 찾기 (보통 "Zscaler", "<회사명> Root CA" 같은 이름)
#      -> 마우스 우클릭 -> 모든 작업 -> 내보내기 -> Base-64 X.509 (.CER)
#      -> C:\corp-ca.pem 으로 저장
#
#   2) PowerShell에서:
#      [Environment]::SetEnvironmentVariable("REQUESTS_CA_BUNDLE","C:\corp-ca.pem","User")
#      [Environment]::SetEnvironmentVariable("SSL_CERT_FILE",    "C:\corp-ca.pem","User")
#
#   3) 새 PowerShell 창 열고 다시 실행.
#
# 절대로 verify=False 로 우회하지 말 것. MITM 무방비.
# =============================================================================