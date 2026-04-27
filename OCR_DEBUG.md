# Debugar Problema de OCR

Se a automação está pedindo nome manualmente mesmo com Tesseract, aqui está como debugar:

## 1. Verificar se Tesseract está instalado

Abra PowerShell:
```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

Deve mostrar a versão. Se não encontrar, instale conforme: [TESSERACT_INSTALL.md](./TESSERACT_INSTALL.md)

## 2. Verificar Logs de Execução

Quando rodar a automação, procure nos logs por:

```
🔍 Executando OCR (Tesseract: ...)
📊 OCR Result - Confidence: X% | Text: 'xxx'
📁 Debug image saved: out/debug_ocr_0001.png
```

### Se ver "❌ OCR Exception"
- Tesseract pode não estar instalado
- Ou o caminho está errado
- Verifique em `automation_config.json`: `tesseract_cmd`

### Se ver "⚠️ OCR Confidence too low"
- Tesseract funcionou mas o texto saiu com baixa confiança
- A região `customer_name_region` pode estar incorreta
- Abra `out/debug_ocr_0001.png` para verificar o que foi capturado

## 3. Verificar Imagens de Debug

Depois de cada execução, você vai ter arquivos em `out/`:
- `debug_ocr_0001.png` - O que foi capturado
- `debug_ocr_0002.png` - Segundo pedido
- etc

**Abra essas imagens e veja:**
- ✅ O nome do cliente está visível e legível?
- ✅ A imagem tem bom contraste?
- ✅ Não tem partes extras indesejadas?

Se não, a região está errada. Precisa recalibrar!

## 4. Recalibrar a Região

Use o calibrador para encontrar a posição correta:

```powershell
.\.venv\Scripts\python.exe .\calibrate.py
```

Meça a região que contém o nome. Edite `automation_config.json`:

```json
{
  "customer_name_region": [LEFT, TOP, WIDTH, HEIGHT]
}
```

Exemplo:
```json
{
  "customer_name_region": [100, 200, 300, 50]
}
```

## 5. Aumentar Verbosidade de Logs

Se ainda tiver dúvida, edite `src/main.py` para ver ainda mais logs:

Procure por:
```python
logging.basicConfig(
    level=logging.INFO,
    ...
)
```

Mude para:
```python
logging.basicConfig(
    level=logging.DEBUG,
    ...
)
```

Assim você verá todos os detalhes incluindo imagens processadas.

## Checklist Rápido

- [ ] Tesseract instalado em `C:\Program Files\Tesseract-OCR\`
- [ ] `automation_config.json` tem `customer_name_region` correto
- [ ] Imagens em `out/debug_ocr_*.png` mostram o nome corretamente
- [ ] Logs mostram confidence > 20%

Se tudo isso estiver OK, OCR deve funcionar!

## Ainda não funciona?

Compartilhe comigo:
1. Uma imagem de `out/debug_ocr_0001.png`
2. Os logs que mostram a confiança
3. A região que você calibrou em `automation_config.json`
