#!/usr/bin/env powershell
<#
.DESCRIPTION
Instala Tesseract OCR para Windows com suporte a português
#>

param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Verificando Tesseract OCR..." -ForegroundColor Cyan

# Verifica se Tesseract está instalado
$TesseractPaths = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "$env:ProgramFiles\Tesseract-OCR\tesseract.exe"
)

$Installed = $false
foreach ($Path in $TesseractPaths) {
    if (Test-Path $Path) {
        Write-Host "✅ Tesseract já está instalado em: $Path" -ForegroundColor Green
        $Installed = $true
        break
    }
}

if ($Installed) {
    Write-Host "✅ OCR pronto para usar!" -ForegroundColor Green
    exit 0
}

Write-Host "❌ Tesseract não encontrado. Instalando..." -ForegroundColor Yellow

# Tenta com winget (mais rápido)
try {
    Write-Host "📥 Instalando via winget..." -ForegroundColor Cyan
    winget install -e --id=UB.Tesseract --silent --accept-package-agreements --accept-source-agreements | Out-Null
    
    if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
        Write-Host "✅ Tesseract instalado com sucesso!" -ForegroundColor Green
        exit 0
    }
}
catch {
    Write-Host "⚠️  winget não disponível ou falhou, tentando instalador direto..." -ForegroundColor Yellow
}

# Alternativa: Baixar instalador
$DownloadUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.0/tesseract-ocr-w64-setup-v5.3.0.exe"
$InstallerPath = "$env:TEMP\tesseract-installer.exe"

try {
    Write-Host "📥 Baixando Tesseract v5.3.0..." -ForegroundColor Cyan
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $InstallerPath -UseBasicParsing
    
    Write-Host "💾 Instalando..." -ForegroundColor Cyan
    & $InstallerPath /S /D="C:\Program Files\Tesseract-OCR" | Out-Null
    
    Start-Sleep -Seconds 3
    
    if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
        Write-Host "✅ Tesseract instalado com sucesso!" -ForegroundColor Green
        Write-Host "📍 Localização: C:\Program Files\Tesseract-OCR" -ForegroundColor Cyan
        
        # Limpa arquivo temporário
        Remove-Item $InstallerPath -Force -ErrorAction SilentlyContinue
        exit 0
    }
    else {
        throw "Tesseract não foi encontrado após instalação"
    }
}
catch {
    Write-Host "❌ Erro ao instalar Tesseract: $_" -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "⚠️  Instalação manual necessária:" -ForegroundColor Yellow
    Write-Host "   1. Visite: https://github.com/UB-Mannheim/tesseract/releases" -ForegroundColor White
    Write-Host "   2. Baixe: tesseract-ocr-w64-setup-v5.3.0.exe" -ForegroundColor White
    Write-Host "   3. Execute e instale em: C:\Program Files\Tesseract-OCR" -ForegroundColor White
    exit 1
}
