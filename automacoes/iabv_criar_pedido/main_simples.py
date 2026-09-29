#!/usr/bin/env python3
"""
Automação: Criar Pedido IABV — Versão Simples (teste)

Fluxo fixo por teclado, sem clicar em coordenadas e sem verificação de campo —
só digita e deixa o próprio Ucom619 mover o cursor entre os campos com Enter:

  código -> espera 2s -> Enter -> espera 5s
  -> quantidade -> espera 1s -> Enter -> espera 1s -> Enter -> espera 1s
  -> desconto -> F5 -> espera 6s -> próximo item

Não mexe em main.py (fluxo por coordenadas) — é uma etapa separada pra
comparar qual abordagem é mais confiável.
"""

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

sys.path.insert(0, str(Path(__file__).parent))
from main import TXT_PATH, _parse_txt  # reaproveita o parser do CRIAR PEDIDO.txt

pyautogui.FAILSAFE = True  # mover o mouse ao canto superior esquerdo aborta o script


def _digitar(valor: str) -> None:
    """Cola o valor via clipboard (garante vírgula/acentos) no campo que
    estiver com foco no momento — sem clicar em nada."""
    pyperclip.copy(valor)
    pyautogui.hotkey('ctrl', 'v')


def _processar_item(item: dict, index: int, total: int) -> None:
    code = item['code']
    qty = item['qty']
    discount = item['discount']
    skip_discount = item['skip_discount']

    desc_info = "sem desconto (**)" if skip_discount else f"desconto: {discount}%"
    print(f"[{index}/{total}] Código: {code} | Qtd: {qty} | {desc_info}")

    _digitar(code)
    time.sleep(2)
    pyautogui.press('enter')
    time.sleep(5)

    _digitar(qty)
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)

    if not skip_discount:
        _digitar(discount)

    pyautogui.press('f5')
    time.sleep(6)


def main() -> None:
    print("Modo: Criar Pedido (Teste Simples - por teclado)")
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
        _processar_item(item, i, len(items))

    print("\nAutomação concluída!")


if __name__ == "__main__":
    main()
