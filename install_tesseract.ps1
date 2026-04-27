#!/usr/bin/env powershell
# Verifica Tesseract OCR

$TesseractPaths = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "$env:ProgramFiles\Tesseract-OCR\tesseract.exe"
)

$Installed = $false
$FoundPath = ""

foreach ($Path in $TesseractPaths) {
    if (Test-Path $Path) {
        $Installed = $true
        $FoundPath = $Path
        break
    }
}

if ($Installed) {
    Write-Host "Tesseract encontrado em: $FoundPath"
    exit 0
}

Write-Host "Tesseract nao encontrado em: $($TesseractPaths[0])"
Write-Host ""
Write-Host "Para instalar manualmente:"
Write-Host "  1. Visite: https://github.com/UB-Mannheim/tesseract/releases"
Write-Host "  2. Baixe a versao mais recente (tesseract-ocr-w64-setup-v*.exe)"
Write-Host "  3. Execute e instale em: C:\Program Files\Tesseract-OCR"
Write-Host "  4. Reinicie a automacao"
Write-Host ""
Write-Host "Ou instale via winget (se disponivel):"
Write-Host "  winget install -e --id=UB.Tesseract"

exit 1
