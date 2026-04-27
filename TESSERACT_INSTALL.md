# Instalação de Tesseract OCR

## Por que Tesseract?

Tesseract é uma ferramenta de **OCR (Optical Character Recognition)** que extrai texto de imagens.
Na automação, ele é usado para ler o nome do cliente automaticamente da tela.

**Sem Tesseract:** Você terá que digitar o nome de cada cliente manualmente em um popup.
**Com Tesseract:** O nome é extraído automaticamente e salvo junto com o PDF.

## Instalação Rápida

### Opção 1: Via GitHub (Recomendado)

1. Acesse: https://github.com/UB-Mannheim/tesseract/releases
2. Baixe a versão mais recente: `tesseract-ocr-w64-setup-v5.3.0.exe` (ou versão maior)
3. Execute o instalador
4. **Importante:** Instale em `C:\Program Files\Tesseract-OCR` (caminho padrão)
5. Conclua a instalação
6. Reinicie a automação

### Opção 2: Via winget (se disponível)

```powershell
winget install -e --id=UB.Tesseract
```

## Verificar Instalação

Abra PowerShell e execute:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

Se aparecer a versão → Pronto! ✅

## Solução de Problemas

### "Tesseract não encontrado"

Certifique-se que está instalado em: `C:\Program Files\Tesseract-OCR\`

Se instalou em outro local, edite `automation_config.json`:

```json
{
  "tesseract_cmd": "C:\\seu\\caminho\\tesseract.exe"
}
```

### OCR com baixa confiança

Se a confiança do OCR estiver abaixo de 30%, a automação pedirá para digitar manualmente.

Para melhorar:
1. Verifique se a `customer_name_region` está correta
2. Ajuste o brilho/contraste do seu monitor
3. Verifique as imagens de debug: `out/debug_ocr_*.png`

## Usando sem Tesseract

Se não conseguir instalar, a automação continuará funcionando:
- Abre um popup para cada pedido
- Você digita o nome
- Continua normalmente

Não é ideal, mas funciona!
