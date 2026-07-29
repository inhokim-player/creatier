# Creatier local server - port conflict handler
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$BasePort = 8100
if ($env:CREATIER_PORT -match '^\d+$') {
    $BasePort = [int]$env:CREATIER_PORT
}
$env:CREATIER_ENV = "development"
$env:CREATIER_PORT = "$BasePort"

function Test-CreatierHealth([int]$Port) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200 -and ($r.Content -match '"app"\s*:\s*"creatier"')) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

function Get-PortListeners([int]$Port) {
    $rows = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $rows) { return @() }
    return @($rows | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-CreatierOnPort([int]$Port) {
    foreach ($procId in (Get-PortListeners $Port)) {
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
            $cmd = $proc.CommandLine
            if ($cmd -and ($cmd -match 'creatier\\server\\app\.py' -or $cmd -match 'creatier/server/app\.py')) {
                Write-Host "[cleanup] stop old creatier PID $procId on port $Port"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        } catch {
            # ignore
        }
    }
    Start-Sleep -Milliseconds 800
}

function Test-PortFree([int]$Port) {
    $listeners = Get-PortListeners $Port
    return ($listeners.Count -eq 0)
}

if (Test-CreatierHealth $BasePort) {
    Write-Host ""
    Write-Host "Creatier already running: http://localhost:$BasePort"
    Start-Process "http://localhost:$BasePort"
    exit 0
}

Stop-CreatierOnPort $BasePort

python -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[error] pip install failed"
    exit 1
}

$Port = $BasePort
$max = $BasePort + 10
while ($Port -le $max) {
    if (Test-PortFree $Port) {
        break
    }
    if (Test-CreatierHealth $Port) {
        Write-Host ""
        Write-Host "Creatier already running: http://localhost:$Port"
        Start-Process "http://localhost:$Port"
        exit 0
    }
    Write-Host "[info] port $Port busy, try $($Port + 1)"
    $Port++
}

if ($Port -gt $max) {
    Write-Host "[error] no free port between $BasePort and $max"
    exit 1
}

$env:CREATIER_PORT = "$Port"
$portFile = Join-Path $Root "data\.local-port"
New-Item -ItemType Directory -Force -Path (Split-Path $portFile) | Out-Null
Set-Content -Path $portFile -Value "$Port" -Encoding ASCII

Write-Host ""
Write-Host "Creatier: http://localhost:$Port"
Write-Host "Admin:    http://localhost:$Port/login"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

Start-Process "http://localhost:$Port"
python server/app.py
