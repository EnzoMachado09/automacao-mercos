# Instalação de Tesseract OCR

## Por que Tesseract?

Tesseract é uma ferramenta de **OCR (Optical Character Recognition)** que extrai texto de imagens.
Na automação, ele é usado para ler o nome do cliente automaticamente da tela.

**Sem Tesseract:** Você terá que digitar o nome de cada cliente manualmente em um popup.
**Com Tesseract:** O nome é extraído automaticamente e salvo junto com o PDF.

## Instalação Rápida (Windows)

### Opção 1: UB Mannheim (Recomendado - mais fácil)

1. Acesse: **https://github.com/UB-Mannheim/tesseract/wiki**
2. Clique em **"Downloads"** (lado esquerdo)
3. Procure por: `tesseract-ocr-w64-setup-v*.exe` (versão mais recente para 64-bit)
4. Execute o instalador
5. **Importante:** Mantenha o caminho padrão: `C:\Program Files\Tesseract-OCR`
6. Conclua a instalação
7. Reinicie a automação

### Opção 2: Repositório Oficial

1. Acesse: https://github.com/tesseract-ocr/tesseract/releases
2. Procure por versão de Windows (`.exe` ou `.msi`)
3. Siga os mesmos passos acima

### Opção 3: Via winget (Menos confiável)

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
