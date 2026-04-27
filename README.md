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

### OCR para Extração Automática de Nomes (Recomendado)

A automação usa **Tesseract OCR** para extrair os nomes dos clientes automaticamente. Sem Tesseract, você terá que digitar manualmente.

#### Instalação Automática (Recomendado)

Ao abrir o launcher, se Tesseract não estiver instalado, você verá um popup oferecendo instalação automática. Clique **SIM** para instalar.

#### Instalação Manual

Se a instalação automática não funcionar:

1. Visite: https://github.com/UB-Mannheim/tesseract/releases
2. Baixe: `tesseract-ocr-w64-setup-v5.3.0.exe` (ou versão mais recente)
3. Execute e instale em: `C:\Program Files\Tesseract-OCR`
4. Reinicie a aplicação

#### Verificar Instalação

Abra PowerShell e digite:
```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
```

Se mostrar a versão, está instalado! ✅

#### Debug de OCR

Se o OCR não está funcionando bem:

1. Verifique se a região `customer_name_region` está correta em `automation_config.json`
2. Cada execução gera screenshots de debug em `out/debug_ocr_0001.png`, etc
3. Abra essas imagens para verificar se o nome está sendo capturado corretamente

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
