# URACE installer for Windows — downloads the pre-built binary or builds from source.
#
# Usage (run in PowerShell as user, no elevation required):
#   irm https://raw.githubusercontent.com/urace/urace/main/install.ps1 | iex
#   .\install.ps1 [-Version 0.9.3] [-InstallDir C:\Users\you\.local\bin]
#
# Installs to InstallDir (default: $HOME\.local\bin) and adds it to the user PATH.
# Falls back to `cargo install urace` if no pre-built binary is available.

[CmdletBinding()]
param(
    [string]$Version    = "latest",
    [string]$InstallDir = "$HOME\.local\bin"
)

$ErrorActionPreference = "Stop"
$Repo = "urace/urace"
$Target = "x86_64-pc-windows-msvc"

function Write-Info  { param($Msg) Write-Host "[urace] $Msg" -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "[urace] $Msg" -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Error "[urace] $Msg" }

function Get-LatestVersion {
    $api = "https://api.github.com/repos/$Repo/releases/latest"
    try {
        $resp = Invoke-RestMethod -Uri $api -UseBasicParsing
        return $resp.tag_name
    } catch {
        return $null
    }
}

function Install-FromRelease {
    $ver = if ($Version -eq "latest") { Get-LatestVersion } else { $Version }
    if (-not $ver) {
        Write-Warn "Could not resolve latest version — falling back to cargo install"
        return $false
    }

    $archive = "urace-$ver-$Target.zip"
    $url = "https://github.com/$Repo/releases/download/$ver/$archive"
    $tmp = Join-Path $env:TEMP "urace-install-$([System.IO.Path]::GetRandomFileName())"
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null

    Write-Info "Downloading urace $ver for $Target..."
    try {
        Invoke-WebRequest -Uri $url -OutFile "$tmp\urace.zip" -UseBasicParsing
    } catch {
        Write-Warn "Pre-built binary not found for $Target — falling back to cargo install"
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }

    Expand-Archive -Path "$tmp\urace.zip" -DestinationPath $tmp -Force

    $exe = Get-ChildItem -Path $tmp -Filter "urace.exe" -Recurse | Select-Object -First 1
    if (-not $exe) {
        Write-Warn "urace.exe not found in archive — falling back to cargo install"
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        return $false
    }

    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Copy-Item $exe.FullName "$InstallDir\urace.exe" -Force
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

    Write-Info "Installed urace $ver to $InstallDir\urace.exe"
    return $true
}

function Install-FromCargo {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        Write-Err "cargo not found. Install Rust from https://rustup.rs — then re-run this script."
    }
    Write-Info "Building from source via cargo (this takes a few minutes)..."
    $root = Split-Path $InstallDir -Parent
    if ($Version -eq "latest") {
        cargo install urace --root $root --quiet
    } else {
        cargo install urace --version $Version --root $root --quiet
    }
    Write-Info "Installed urace to $InstallDir\urace.exe"
}

function Add-ToUserPath {
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$InstallDir*") {
        [System.Environment]::SetEnvironmentVariable(
            "PATH", "$userPath;$InstallDir", "User"
        )
        Write-Info "Added $InstallDir to your user PATH (restart your terminal to pick it up)"
    }
    # Also update the current session
    $env:PATH = "$env:PATH;$InstallDir"
}

function Main {
    Write-Info "Installing URACE..."

    $ok = Install-FromRelease
    if (-not $ok) { Install-FromCargo }

    Add-ToUserPath

    Write-Info ""
    Write-Info "Run: urace --help"
    Write-Info "Docs: https://github.com/urace/urace"
}

Main
