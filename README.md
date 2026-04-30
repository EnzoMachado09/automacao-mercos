# Automação Mercos

Automação ponta-a-ponta para o fluxo de pedidos da IABV no sistema Mercos. Cobre da exportação de pedidos do sistema desktop até a recriação automática deles no Mercos Web, passando por uma etapa intermediária de extração de dados.

## Visão geral das etapas

| Etapa | Entrada | Saída | Tecnologia |
|-------|---------|-------|------------|
| **Etapa 1** | Lista de pedidos no Mercos Desktop | PDFs nomeados por cliente | PyAutoGUI + OCR (Tesseract) |
| **Etapa 2** | Excels de pedidos exportados | `[CLIENTE] M.xlsx` + `[CLIENTE] M.json` (cliente, CNPJ, data) | openpyxl |
| **Etapa 3** | Pares `M.xlsx` + `M.json` | Pedidos criados no Mercos Web | Playwright |

Todas as etapas são executadas pelo `hotkey_launcher.py` (interface gráfica + hotkey F6).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Para a Etapa 1, instale também o **Tesseract OCR**: ver [TESSERACT_INSTALL.md](TESSERACT_INSTALL.md).

## Configuração

Cada etapa tem seu próprio JSON. Os arquivos `*.example.json` servem de template — copie para `*.json` (sem `.example`) e preencha. Os arquivos sem `.example` ficam ignorados pelo git por conterem credenciais ou caminhos pessoais.

```bash
cp etapa2_config.example.json etapa2_config.json
cp etapa3_config.example.json etapa3_config.json
cp automation_config.example.json automation_config.json
```

### `etapa3_config.json` (credenciais Mercos Web)
```json
{
  "mercos_url": "https://app.mercos.com",
  "email": "seu-email@exemplo.com",
  "senha": "sua-senha",
  "representada": "NOME_DA_REPRESENTADA",
  "condicao_pagamento": "a vista",
  "output_dir": "C:\\caminho\\PEDIDOS EM EXCEL"
}
```

### `etapa2_config.json` (caminhos do fluxo Excel)
```json
{
  "modelo_path": "C:\\caminho\\Planilha Modelo",
  "pedidos_input_dir": "C:\\caminho\\PDF PARA EXCEL",
  "output_dir": "C:\\caminho\\PEDIDOS EM EXCEL"
}
```

### `automation_config.json` (coordenadas do Mercos Desktop — Etapa 1)
Use o `calibrate.py` para descobrir as coordenadas da sua tela.

## Execução

### Modo padrão: launcher gráfico
```bash
start_launcher.bat
```
Selecione a etapa, configure os parâmetros e use **F6** para iniciar/parar. **ESC** fecha a aplicação.

### Modo direto (CLI)

```bash
# Etapa 1 (PDFs do Mercos Desktop)
python -m src.main --output-dir "C:\Pedidos\PDF" --max-orders 10

# Etapa 2 (extração Excel)
python main_etapa2.py

# Etapa 3 (criação no Mercos Web)
python main_etapa3.py
```

## Calibração da Etapa 1

Para descobrir as coordenadas da sua tela:

```bash
.venv\Scripts\python.exe calibrate.py
```

- Posicione o mouse sobre o ponto desejado.
- Pressione **Enter** ou clique em "Capturar" — copia `[x, y]` para a área de transferência.
- Cole no `automation_config.json`.

## Estrutura

```
.
├── hotkey_launcher.py      # Interface gráfica principal (F6 para iniciar/parar)
├── main_etapa2.py          # Entry point Etapa 2
├── main_etapa3.py          # Entry point Etapa 3
├── calibrate.py            # Ferramenta de calibração (Etapa 1)
├── start_launcher.bat      # Atalho para abrir o launcher
├── src/
│   ├── main.py             # Entry point Etapa 1
│   ├── automation.py       # Lógica da Etapa 1 (PyAutoGUI + OCR)
│   ├── config.py           # Carregamento de configuração da Etapa 1
│   ├── vision.py           # OCR com Tesseract
│   ├── excel_automation.py # Lógica da Etapa 2 (openpyxl)
│   └── mercos_web_automation.py  # Lógica da Etapa 3 (Playwright)
├── *.example.json          # Templates de configuração
└── out/                    # Logs e screenshots de debug
```

## Arquivos sensíveis (não vão para o git)

- `*_config.json` (sem o `.example`) — contêm credenciais e caminhos pessoais
- `playwright_profile/` — perfil persistente do Chrome (mantém sessão Mercos logada)
- `out/*.png`, `out/*.log` — screenshots e logs gerados em runtime
