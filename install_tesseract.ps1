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
Write-Host "  1. Visite: https://github.com/UB-Mannheim/tesseract/wiki"
Write-Host "  2. Clique em 'Downloads' (lado esquerdo)"
Write-Host "  3. Baixe: tesseract-ocr-w64-setup-v*.exe (versao mais recente)"
Write-Host "  4. Execute e instale em: C:\Program Files\Tesseract-OCR"
Write-Host "  5. Reinicie a automacao"
Write-Host ""
Write-Host "Ou visite o repositorio oficial:"
Write-Host "  https://github.com/tesseract-ocr/tesseract/releases"

exit 1
