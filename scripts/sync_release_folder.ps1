# GitHub 업로드용 — CREATIER-RELEASE 폴더 동기화 (기존 .git 유지)
$ErrorActionPreference = "Stop"
$Creatier = Split-Path -Parent $PSScriptRoot
$Repo = Split-Path -Parent $Creatier
$Src = $Creatier
$Dst = Join-Path $Repo "CREATIER-RELEASE"

$excludeDirs = @("__pycache__", ".git")
$excludeFiles = @(".env", "creatier.db", "mail-log.json", ".railway-auth-secret", "RAILWAY-VARIABLES.txt", "build_release_zip.py")

function ShouldSkip([string]$rel) {
    $parts = $rel -split '[\\/]'
    foreach ($p in $excludeDirs) { if ($parts -contains $p) { return $true } }
    $name = Split-Path $rel -Leaf
    if ($excludeFiles -contains $name) { return $true }
    if ($name -like "*.pyc") { return $true }
    if ($name -eq ".local-port") { return $true }
    if ($rel -like "scripts/build_release_zip.py") { return $true }
    return $false
}

Get-ChildItem $Src -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Src.Length + 1)
    if (ShouldSkip $rel) { return }
    $target = Join-Path $Dst $rel
    $dir = Split-Path $target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Copy-Item $_.FullName $target -Force
}

$rootFiles = @(
    "Procfile", "railway.json", "nixpacks.toml", "runtime.txt", "requirements.txt",
    ".gitignore", "CREATIER-RAILWAY.md", "CREATIER-DEPLOY.md", "CREATIER-출시체크리스트.md"
)
foreach ($name in $rootFiles) {
    $src = Join-Path $Src $name
    if (Test-Path $src) { Copy-Item $src (Join-Path $Dst $name) -Force }
}

Remove-Item (Join-Path $Dst "RAILWAY-VARIABLES.txt") -ErrorAction SilentlyContinue

Write-Host "Synced: $Dst"
