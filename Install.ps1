<#
.SYNOPSIS
    DubStage Studio Windows MSIX Sideloading & Installation Helper Script
.DESCRIPTION
    Installs the code signing certificate into the local machine Trusted People store
    and installs the DubStage .msix package.
#>

[CmdletBinding()]
param()

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DubStage Studio - Windows MSIX Installation Helper      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Check for Administrator elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] Elevating PowerShell process with Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $MyInvocation.MyCommand.Path) -Verb RunAs
    exit
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Install Certificate if present
$certFile = Get-ChildItem -Path $scriptDir -Filter "*.cer" | Select-Object -First 1
if ($certFile) {
    Write-Host "[1/2] Installing Certificate: $($certFile.Name) into TrustedPeople..." -ForegroundColor Yellow
    try {
        Import-Certificate -FilePath $certFile.FullName -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" -ErrorAction Stop | Out-Null
        Import-Certificate -FilePath $certFile.FullName -CertStoreLocation "Cert:\LocalMachine\Root" -ErrorAction SilentlyContinue | Out-Null
        Write-Host "      ✓ Certificate installed successfully." -ForegroundColor Green
    } catch {
        Write-Warning "Failed to install certificate: $_"
    }
} else {
    Write-Host "[1/2] No .cer certificate found in directory. Skipping cert installation." -ForegroundColor DarkGray
}

# 2. Install MSIX Package
$msixFile = Get-ChildItem -Path $scriptDir -Filter "*.msix" | Select-Object -First 1
if ($msixFile) {
    Write-Host "[2/2] Installing DubStage MSIX Package: $($msixFile.Name)..." -ForegroundColor Yellow
    try {
        Add-AppxPackage -Path $msixFile.FullName -ErrorAction Stop

        # Verify package registration in Windows
        $pkg = Get-AppxPackage -Name "DubStageStudio"
        if ($pkg) {
            Write-Host "      ✓ DubStage successfully registered and installed to Windows!" -ForegroundColor Green
            Write-Host "      Package Full Name: $($pkg.PackageFullName)" -ForegroundColor DarkGray
            Write-Host ""
            Write-Host "You can now launch 'DubStage' from the Windows Start Menu." -ForegroundColor Cyan
        } else {
            Write-Warning "Add-AppxPackage command completed, but Get-AppxPackage did not find 'DubStageStudio'. Please check Windows Event Viewer (AppXDeployment-Server)."
        }
    } catch {
        Write-Host "      ✗ Installation Failed!" -ForegroundColor Red
        Write-Host "Error Details: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "1. Ensure Developer Mode is enabled under Windows Settings > System > For Developers." -ForegroundColor Yellow
        Write-Host "2. Ensure the self-signed certificate was trusted in Trusted People store." -ForegroundColor Yellow
    }
} else {
    Write-Error "No .msix package found in directory: $scriptDir"
}

Write-Host ""
Write-Host "Press any key to close this window..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
