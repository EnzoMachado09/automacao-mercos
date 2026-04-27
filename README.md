# Automacao Mercos

Automacao em Python para exportar pedidos do sistema desktop da Mercos para PDF e salvar os arquivos com o nome do cliente.

## Como funciona na versao inicial

- O fluxo assume Windows e foco controlado na janela do sistema desktop.
- A navegacao pela tela de pedidos e feita por teclado e cliques configuraveis.
- A leitura do nome do cliente pode usar OCR opcional, com fallback para digitar manualmente.
- A deteccao do fim da lista depende de uma regiao de monitoramento configuravel na tela.

## Dependencias

Instale as dependencias com:

```bash
pip install -r requirements.txt
```

OCR e opcional. Se quiser extrair o nome do cliente automaticamente, instale tambem o Tesseract no Windows e ajuste o PATH.

## Execucao

Usando o launcher PowerShell:

```powershell
powershell -File run.ps1 -StartDate 01/04/2026 -EndDate 27/04/2026 -OutputDir "C:\Pedidos\PDF"
```

Usando o launcher em lote:

```bat
run.bat 01/04/2026 27/04/2026 "C:\Pedidos\PDF"
```

Ou, diretamente com o modulo Python:

```bash
python -m src.main --start-date 01/04/2026 --end-date 27/04/2026 --output-dir "C:\\Pedidos\\PDF"
```

## Calibracao de tela

Para descobrir as posicoes dos cliques e regioes da sua tela, execute:

```powershell
.\.venv\Scripts\python.exe .\calibrate.py
```

Uso do calibrador:

- Posicione o mouse sobre o ponto que quer medir.
- Leia as coordenadas na janela do calibrador.
- Clique em `Capturar` ou pressione `Enter` para copiar `[x, y]` para a area de transferencia.
- Clique em `Salvar Screenshot` para gravar uma imagem da tela atual em `screenshots\calibracao_tela.png`.

Depois me envie os pontos da tela real para eu preencher os lugares faltantes no `automation_config.json`.

## Configuracao

Crie um arquivo chamado `automation_config.json` na raiz do projeto para calibrar coordenadas e regioes da interface.

Campos principais sugeridos:

- `export_pdf_button`: coordenada do icone de exportar para PDF.
- `customer_name_region`: regiao da tela onde aparece o nome do cliente.
- `selection_probe_region`: regiao que muda quando a selecao da grade muda.
- `advance_key`: tecla usada para descer para o proximo pedido.
- `report_variation_down_presses`: quantidade de vezes para chegar em `Pedido Geral - IABV`.

## Commit automatico

O repositorio local esta preparado para receber commits frequentes durante a automacao do desenvolvimento.
