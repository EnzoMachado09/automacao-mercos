#!/usr/bin/env python3
"""
Automação: Criar / Editar Pedidos IABV
Lê CRIAR PEDIDO.txt e lança ou edita itens no sistema IABV via PyAutoGUI.

Modo Criar (padrão):
  CODIGO - QTDun - DESCONTO% / ...   (ex: 2110 - 20un - 62,98% / 07.05.2026)
  CODIGO** - QTDun                   (** pula campo de desconto)

Modo Editar (--editar):
  Itens existentes:
    CODIGO - QTDun             (só quantidade)
    CODIGO - DESCONTO%         (só desconto)
    CODIGO - QTDun - DESCONTO% (ambos)
  Itens novos no pedido (!! no código - segue fluxo de criar):
    CODIGO!! - QTDun - DESCONTO%
    CODIGO!! - QTDun
    CODIGO!!** - QTDun         (** pula desconto, igual ao criar)
  Itens ignorados (## no código):
    CODIGO## - ...             (linha pulada, nenhuma ação)
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
            if not re.match(r'^\d[\w-]*$', code):
                continue

            qty_match = re.match(r'\d+', parts[1])
            if not qty_match:
                continue
            qty = int(qty_match.group())

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


def _fechar_popup_se_aberto() -> None:
    """Fecha o popup Ucom619 de aviso de cálculo de desconto, ignorando outros popups Ucom619."""
    try:
        import ctypes
        import ctypes.wintypes
        user32 = ctypes.windll.user32

        ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        def _texto_filhos(hwnd: int) -> str:
            textos: list[str] = []
            def cb(child, _):
                n = user32.GetWindowTextLengthW(child) + 1
                buf = ctypes.create_unicode_buffer(n)
                user32.GetWindowTextW(child, buf, n)
                if buf.value:
                    textos.append(buf.value)
                return True
            user32.EnumChildWindows(hwnd, ENUMPROC(cb), 0)
            return ' '.join(textos)

        hwnds: list[int] = []
        def enum_cb(hwnd, _):
            n = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(n)
            user32.GetWindowTextW(hwnd, buf, n)
            if "Ucom619" in buf.value:
                hwnds.append(hwnd)
            return True
        user32.EnumWindows(ENUMPROC(enum_cb), 0)

        for hwnd in hwnds:
            conteudo = _texto_filhos(hwnd)
            if "Valor de Desconto" in conteudo:
                print("  [popup] aviso de desconto detectado, fechando...")
                user32.SetForegroundWindow(hwnd)
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(0.5)
    except Exception:
        pass


def _aguardar_apos_f5() -> None:
    """Aguarda após F5, verificando popup Ucom619 logo no início."""
    time.sleep(1.5)
    _fechar_popup_se_aberto()
    time.sleep(DELAY_APOS_F5 - 1.5)


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
        _fechar_popup_se_aberto()
        pyautogui.press('enter')
        time.sleep(DELAY_ETAPA)

        # Digitar apenas o valor numérico do desconto (sem o símbolo %)
        _paste(discount)

        # F5 para gravar o item
        pyautogui.press('f5')

    # Aguarda o sistema processar o item antes do próximo
    _aguardar_apos_f5()


def _parse_txt_editar(path: Path) -> list[dict]:
    """Parse TXT para modo editar pedido."""
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
            if '##' in raw_code:
                continue
            is_new = '!!' in raw_code
            has_star = '**' in raw_code
            code = raw_code.replace('!!', '').replace('**', '').strip()

            if not re.match(r'^\d[\w-]*$', code):
                continue

            if is_new:
                # Novo item: segue fluxo idêntico ao criar pedido
                qty_match = re.match(r'\d+', parts[1])
                if not qty_match:
                    continue
                qty = str(int(qty_match.group()))

                discount = None
                if not has_star and len(parts) >= 3:
                    discount = _parse_discount(parts[2])

                items.append({
                    'code': code,
                    'qty': qty,
                    'discount': discount,
                    'skip_discount': has_star or discount is None,
                    'is_new': True,
                })
            else:
                # Item existente: detectar quais campos estão presentes
                field1 = parts[1]

                if '%' in field1:
                    # Só desconto
                    discount = _parse_discount(field1)
                    if discount is None:
                        continue
                    items.append({
                        'code': code,
                        'qty': None,
                        'discount': discount,
                        'has_qty': False,
                        'has_discount': True,
                        'is_new': False,
                    })
                else:
                    # Quantidade (com ou sem 'un'), talvez desconto em parts[2]
                    qty_match = re.match(r'\d+', field1)
                    if not qty_match:
                        continue
                    qty = str(int(qty_match.group()))

                    discount = None
                    if len(parts) >= 3:
                        discount = _parse_discount(parts[2])

                    items.append({
                        'code': code,
                        'qty': qty,
                        'discount': discount,
                        'has_qty': True,
                        'has_discount': discount is not None,
                        'is_new': False,
                    })

    return items


def _process_item_editar(item: dict, index: int, total: int) -> None:
    code = item['code']
    is_new = item['is_new']

    if is_new:
        desc = f"NOVO | Qtd: {item['qty']} | " + ("sem desconto (**)" if item['skip_discount'] else f"desconto: {item['discount']}%")
    elif item['has_qty'] and item['has_discount']:
        desc = f"qty: {item['qty']} | desconto: {item['discount']}%"
    elif item['has_qty']:
        desc = f"qty: {item['qty']}"
    else:
        desc = f"desconto: {item['discount']}%"

    print(f"[{index}/{total}] Código: {code} | {desc}")

    # Digitar código do produto
    _paste(code)
    pyautogui.press('enter')
    time.sleep(DELAY_ETAPA)

    if is_new:
        # Fluxo idêntico ao criar pedido (sem enter extra)
        _paste(item['qty'])
        time.sleep(DELAY_ETAPA)

        if item['skip_discount']:
            pyautogui.press('f5')
        else:
            pyautogui.press('enter')
            time.sleep(DELAY_ETAPA)
            _fechar_popup_se_aberto()
            pyautogui.press('enter')
            time.sleep(DELAY_ETAPA)
            _paste(item['discount'])
            pyautogui.press('f5')
    else:
        # Enter extra para navegar até o item existente no pedido
        pyautogui.press('enter')
        time.sleep(DELAY_ETAPA)

        if item['has_qty'] and item['has_discount']:
            _paste(item['qty'])
            pyautogui.press('enter')
            time.sleep(DELAY_ETAPA)
            _fechar_popup_se_aberto()
            pyautogui.press('enter')
            time.sleep(DELAY_ETAPA)
            _paste(item['discount'])
            pyautogui.press('f5')
        elif item['has_qty']:
            _paste(item['qty'])
            pyautogui.press('f5')
        else:
            # Só desconto: pular campo de quantidade com Enter
            pyautogui.press('enter')
            time.sleep(DELAY_ETAPA)
            _paste(item['discount'])
            pyautogui.press('f5')

    _aguardar_apos_f5()


def main() -> None:
    editar_mode = '--editar' in sys.argv
    modo_label = "Editar Pedido" if editar_mode else "Criar Pedido"

    print(f"Modo: {modo_label}")
    print(f"Lendo: {TXT_PATH}")

    if not TXT_PATH.exists():
        print(f"ERRO: Arquivo não encontrado: {TXT_PATH}")
        sys.exit(1)

    items = _parse_txt_editar(TXT_PATH) if editar_mode else _parse_txt(TXT_PATH)

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
        if editar_mode:
            _process_item_editar(item, i, len(items))
        else:
            _process_item(item, i, len(items))

    print("\nAutomação concluída!")


if __name__ == "__main__":
    main()
