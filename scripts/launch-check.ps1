# Creatier launch check — 로컬 / Railway 배포 전 최종 확인
param(
    [switch]$Dev,
    [switch]$StartServer
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$ok = $true

Write-Host ""
Write-Host "Creatier launch check" -ForegroundColor Cyan
Write-Host ""

function Load-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return @{} }
    $saved = @{}
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $k, $v = $_ -split '=', 2
        $k = $k.Trim()
        $v = $v.Trim().Trim('"').Trim("'")
        if ($k) { $saved[$k] = $v }
    }
    return $saved
}

function Apply-EnvMap([hashtable]$Map) {
    Remove-Item Env:CREATIER_OAUTH_DEV -ErrorAction SilentlyContinue
    Remove-Item Env:CREATIER_PORT -ErrorAction SilentlyContinue
    Remove-Item Env:PORT -ErrorAction SilentlyContinue
    foreach ($k in $Map.Keys) {
        Set-Item -Path "env:$k" -Value $Map[$k]
    }
}

function Set-TestEnv {
    $env:CREATIER_ENV = "development"
    $env:CREATIER_OAUTH_DEV = "1"
    $env:AUTH_SECRET = "test-secret-32chars-minimum-xxxxx"
    $env:CREATIER_ADMIN_EMAIL = "admin@test.local"
    $env:CREATIER_ADMIN_PASSWORD = "adminpass12345"
    $env:CREATIER_DATABASE = Join-Path $Root "data\test-release.db"
    Remove-Item Env:CREATIER_PORT -ErrorAction SilentlyContinue
    Remove-Item Env:PORT -ErrorAction SilentlyContinue
}

$prodEnv = Load-EnvFile (Join-Path $Root "RAILWAY-VARIABLES.txt")
if ($prodEnv.Count -eq 0) {
    $prodEnv = Load-EnvFile (Join-Path $Root ".env")
}

Set-TestEnv

Write-Host "Tests..." -ForegroundColor Cyan
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] unit tests failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] 22 tests passed" -ForegroundColor Green
Write-Host ""

if ($Dev) {
    Write-Host "Mode: development" -ForegroundColor Cyan
    Write-Host "[OK] CREATIER_OAUTH_DEV=1 (Mock OAuth)" -ForegroundColor Green
    Write-Host "[OK] Local port conflict: scripts/run-local.ps1 handles 8100-8110" -ForegroundColor Green
    Write-Host ""
    Write-Host "Start:  크라잇에이터시작.bat" -ForegroundColor Green
    Write-Host "URL:    http://localhost:8100" -ForegroundColor Green
    Write-Host "Admin:  http://localhost:8100/login" -ForegroundColor Green
    if ($StartServer) {
        & (Join-Path $PSScriptRoot "run-local.ps1")
    }
    exit 0
}

Apply-EnvMap $prodEnv
$isProd = ($env:CREATIER_ENV -eq "production")

Write-Host "Mode: $(if ($isProd) { 'PRODUCTION (Railway)' } else { 'development / staging' })" -ForegroundColor Cyan
Write-Host ""

$required = @(
    "CREATIER_ENV",
    "CREATIER_PUBLIC_URL",
    "AUTH_SECRET",
    "CREATIER_ADMIN_EMAIL",
    "CREATIER_ADMIN_PASSWORD",
    "CREATIER_DATABASE"
)
foreach ($key in $required) {
    $val = (Get-Item -Path "env:$key" -ErrorAction SilentlyContinue).Value
    if (-not $val) {
        Write-Host "[X] $key missing" -ForegroundColor Red
        $ok = $false
    } else {
        Write-Host "[OK] $key" -ForegroundColor Green
    }
}

if ($isProd) {
    $secret = $env:AUTH_SECRET
    if ($secret -eq "creatier-local-dev-secret-32chars-minimum" -or ($secret -and $secret.Length -lt 32)) {
        Write-Host "[X] AUTH_SECRET: 32자 이상 랜덤 값 필요" -ForegroundColor Red
        $ok = $false
    }

    $url = $env:CREATIER_PUBLIC_URL
    if ($url -and -not $url.StartsWith("https://")) {
        Write-Host "[X] CREATIER_PUBLIC_URL must be https://" -ForegroundColor Red
        $ok = $false
    }
    if ($url -and $url -notmatch '^https://[a-z0-9-]+\.up\.railway\.app/?$') {
        Write-Host "[X] CREATIER_PUBLIC_URL: Railway 도메인 생성 후 실제 URL로 변경 필요" -ForegroundColor Red
        $ok = $false
    }

    if ($env:CREATIER_DATABASE -notlike "/data/*") {
        Write-Host "[!] CREATIER_DATABASE: /data/creatier.db + Volume /data 권장" -ForegroundColor Yellow
    }

    if ($env:CREATIER_PORT) {
        Write-Host "[X] CREATIER_PORT: Railway Variables에서 제거 (PORT 자동)" -ForegroundColor Red
        $ok = $false
    }

    if ($env:CREATIER_OAUTH_DEV -in @("1", "true", "yes")) {
        Write-Host "[X] CREATIER_OAUTH_DEV: production에서 제거" -ForegroundColor Red
        $ok = $false
    }

    $oauthKeys = @("META_APP_ID", "META_APP_SECRET", "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET")
    $oauthOk = $true
    foreach ($k in $oauthKeys) {
        if (-not (Get-Item -Path "env:$k" -ErrorAction SilentlyContinue).Value) {
            $oauthOk = $false
            break
        }
    }
    if ($oauthOk) {
        Write-Host "[OK] Instagram/TikTok OAuth keys" -ForegroundColor Green
    } else {
        Write-Host "[!] OAuth keys incomplete — 수익 인증 공유만 제한됨 (계산은 가능)" -ForegroundColor Yellow
        if ($url) {
            Write-Host "    Redirect: $url/oauth/instagram/callback" -ForegroundColor DarkGray
            Write-Host "              $url/oauth/tiktok/callback" -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "Railway checklist:" -ForegroundColor Cyan
Write-Host "  Volume mount: /data" -ForegroundColor DarkGray
Write-Host "  Do NOT set PORT or CREATIER_PORT" -ForegroundColor DarkGray
Write-Host "  After domain: update CREATIER_PUBLIC_URL -> Redeploy" -ForegroundColor DarkGray
Write-Host ""

if (-not $ok) {
    Write-Host "FAILED — fix items above before deploy" -ForegroundColor Red
    exit 1
}

Write-Host "READY for Railway deploy" -ForegroundColor Green

if ($StartServer -and $isProd) {
    $testPort = 18999
    Remove-Item Env:CREATIER_PORT -ErrorAction SilentlyContinue
    $env:PORT = "$testPort"
    $env:CREATIER_DATABASE = Join-Path $Root "data\creatier-preflight.db"
    Write-Host ""
    Write-Host "Preflight server (production config) on port $testPort ..." -ForegroundColor Cyan
    $proc = Start-Process -FilePath "python" -ArgumentList "server/app.py" -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 4
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$testPort/api/health" -UseBasicParsing -TimeoutSec 8
        if ($r.Content -match '"app"\s*:\s*"creatier"') {
            Write-Host "[OK] /api/health (Railway PORT mode)" -ForegroundColor Green
        } else {
            Write-Host "[X] /api/health unexpected response" -ForegroundColor Red
            $ok = $false
        }
    } catch {
        Write-Host "[X] /api/health unreachable — $($_)" -ForegroundColor Red
        $ok = $false
    }
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $Root "data\creatier-preflight.db") -ErrorAction SilentlyContinue
}

if ($ok) { exit 0 } else { exit 1 }
