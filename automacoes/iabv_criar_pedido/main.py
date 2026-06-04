#!/usr/bin/env python3
"""
Automação: Criar Pedidos IABV
Lê CRIAR PEDIDO.txt e lança os itens no sistema IABV via PyAutoGUI.

Formato do TXT (por linha):
  CODIGO - QUANTIDADE - DESCONTO% / ... (resto ignorado)
  Ex: 2110 - 20 - 62,98% / 12.24 / GD 65

Itens com ** no código (ex: 3216**) pulam o campo de desconto.
Itens sem % no campo de desconto também pulam o desconto.
"""

import re
import sys
import time
from pathlib import Path

try:
    import pyautogui
    import pyperclip
except ImportError as e:
    print(f"Dependência não instalada: {e}")
    print("Execute: pip install pyautogui pyperclip")
    sys.exit(1)

TXT_PATH = Path(r"C:\Users\enzop\OneDrive\Área de Trabalho\Temporarios\CRIAR PEDIDO.txt")
DELAY_APOS_F5 = 8    # segundos de espera após gravar cada item
DELAY_ETAPA = 2.0    # segundos entre cada ação dentro do processamento do item

pyautogui.FAILSAFE = True  # mover mouse ao canto superior esquerdo aborta o script


def _parse_discount(s: str) -> str | None:
    """Extrai valor numérico do campo de desconto.

    Prioridade:
      1. Campo começa com número (com ou sem %): '62,98%', '62,98', '65'
      2. Número seguido de % em qualquer posição: '... 62,98% ...'
      3. Palavra-chave DEIXEI: 'GD 68,2 / DEIXEI 65'
    Retorna None apenas se nenhum padrão for encontrado.
    """
    # Campo inicia com número (desconto explícito, % opcional)
    match = re.match(r'\s*(\d+(?:[,\.]\d+)?)\s*%?', s)
    if match:
        return match.group(1)
    # % em qualquer posição da string
    match = re.search(r'(\d+(?:[,\.]\d+)?)\s*%', s)
    if match:
        return match.group(1)
    # DEIXEI <valor>
    match = re.search(r'DEIXEI\s+(\d+(?:[,\.]\d+)?)', s, re.IGNORECASE)
    return match.group(1) if match else None


def _parse_txt(path: Path) -> list[dict]:
    items = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(' - ')]
            if len(parts) < 2:
                continue

            raw_code = parts[0]
            has_star = '**' in raw_code
            code = raw_code.replace('**', '').strip()

            # Pula linhas que não são itens (ex: "NC - AC 527786")
            if not code.isdigit():
                continue

            try:
                qty = int(parts[1])
            except ValueError:
                continue

            discount = None
            if not has_star and len(parts) >= 3:
                discount = _parse_discount(parts[2])

            # Pula desconto se item tem ** OU se não há % encontrado na linha
            skip_discount = has_star or discount is None

            items.append({
                'code': code,
                'qty': str(qty),
                'discount': discount,
                'skip_discount': skip_discount,
            })

    return items


def _paste(text: str) -> None:
    """Cola texto via clipboard para garantir caracteres especiais (vírgula, etc.)."""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(DELAY_ETAPA)


def _process_item(item: dict, index: int, total: int) -> None:
    code = item['code']
    qty = item['qty']
    skip_discount = item['skip_discount']
    discount = item['discount']

    desc_info = "sem desconto (**)" if skip_discount else f"desconto: {discount}%"
    print(f"[{index}/{total}] Código: {code} | Qtd: {qty} | {desc_info}")

    # 1. Digitar código do produto
    _paste(code)
    pyautogui.press('enter')
    time.sleep(DELAY_ETAPA)

    # 2. Digitar quantidade
    _paste(qty)
    time.sleep(DELAY_ETAPA)

    if skip_discount:
        pyautogui.press('f5')
    else:
        # Enter 2x para navegar até o campo de desconto
        pyautogui.press('enter')
        time.sleep(DELAY_ETAPA)
        pyautogui.press('enter')
        time.sleep(DELAY_ETAPA)

        # Digitar apenas o valor numérico do desconto (sem o símbolo %)
        _paste(discount)

        # F5 para gravar o item
        pyautogui.press('f5')

    # Aguarda o sistema processar o item antes do próximo
    time.sleep(DELAY_APOS_F5)


def main() -> None:
    print(f"Lendo: {TXT_PATH}")

    if not TXT_PATH.exists():
        print(f"ERRO: Arquivo não encontrado: {TXT_PATH}")
        sys.exit(1)

    items = _parse_txt(TXT_PATH)

    if not items:
        print("Nenhum item encontrado no arquivo. Verifique o formato.")
        sys.exit(0)

    print(f"{len(items)} itens encontrados.")
    print()

    print("Mantenha o foco na janela do IABV com o cursor no campo de código.")
    print("Iniciando em 3 segundos... (mova o mouse ao canto superior esquerdo para abortar)")
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    print("Iniciando!\n")

    for i, item in enumerate(items, 1):
        _process_item(item, i, len(items))

    print("\nAutomação concluída!")


if __name__ == "__main__":
    main()
