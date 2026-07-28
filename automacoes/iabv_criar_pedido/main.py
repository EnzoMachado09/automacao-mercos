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
DELAY_APOS_F5 = 15   # timeout máximo aguardando tela estabilizar após F5
DELAY_ETAPA = 2.0    # segundos entre cada ação dentro do processamento do item

# Coordenadas (X, Y) de cada campo no Ucom619 com a janela MAXIMIZADA. A
# automação clica direto no campo certo antes de digitar, em vez de navegar
# com Enter (o que desincronizava e jogava a quantidade no campo de %).
# Recalibre com:  python calibrar_campos.py  (posicione o mouse e aperte F2)
CAMPO_CODIGO = (55, 93)
CAMPO_QTD = (58, 208)
CAMPO_QTD_ALT = (55, 174)
CAMPO_DESCONTO = (145, 271)
CAMPO_DESCONTO_ALT = (148, 238)

# O formulário aparece em duas alturas diferentes dependendo do produto, por
# isso cada campo tem mais de uma posição possível. A automação NÃO clica em
# todas: clica na primeira, confere pelo cursor se acertou o campo e só tenta a
# seguinte se errou. (Clicar nas duas seguidas jogava o valor no campo errado.)
CAMPOS_CODIGO = [CAMPO_CODIGO]
CAMPOS_QTD = [CAMPO_QTD, CAMPO_QTD_ALT]
CAMPOS_DESCONTO = [CAMPO_DESCONTO, CAMPO_DESCONTO_ALT]

# Tolerâncias para aceitar que o cursor caiu dentro do campo clicado. Y é
# apertado (os dois layouts ficam ~34px distantes); X é folgado porque o cursor
# pula para o fim do texto existente, à esquerda de onde clicamos.
TOL_CARET_Y = 15
TOL_CARET_X = (-260, 25)
# Botão que fecha o popup que sempre aparece ao EDITAR um item existente
# (substitui o segundo Enter que usávamos para navegar até o item).
POPUP_EDITAR = (1104, 597)

pyautogui.FAILSAFE = True  # mover mouse ao canto superior esquerdo aborta o script


# ---------------------------------------------------------------------------
# Detecção de campo focado (Win32) — identifica em qual campo o cursor está
# para garantir que cada valor é digitado no campo certo (código/qtd/desconto).
# ---------------------------------------------------------------------------

import ctypes
from ctypes import wintypes


class _RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class _POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND),
                ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND),
                ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND),
                ("hwndCaret", wintypes.HWND),
                ("rcCaret", _RECT)]


# Declara os protótipos (restype/argtypes) das funções Win32. Sem isso, o
# ctypes assume retorno c_int (32 bits) e TRUNCA os handles de janela de 64
# bits — o que faz GetWindowRect falhar e devolver retângulos zerados (0,0).
_user32 = ctypes.windll.user32
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetGUIThreadInfo.restype = wintypes.BOOL
_user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(_GUITHREADINFO)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]
_user32.ClientToScreen.restype = wintypes.BOOL
_user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(_POINT)]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.GetAsyncKeyState.restype = ctypes.c_short
_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

# Torna o processo ciente de DPI para que GetWindowRect devolva coordenadas
# reais (sem virtualização) quando a tela tem escala diferente de 100%.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
except Exception:
    try:
        _user32.SetProcessDPIAware()
    except Exception:
        pass


class _SemPermissao(Exception):
    """A janela Ucom619 existe, mas o Windows bloqueou a leitura da geometria
    (normalmente porque o sistema da IABV roda como Administrador e este
    processo não). Solução: rodar este script como Administrador."""


# Faixas (x, y) do CENTRO de cada campo, relativo ao canto superior-esquerdo
# da janela Ucom619. Valores iniciais aproximados do print — calibre com --diag.
_CAMPOS = {
    'codigo':   {'x': (0, 130),   'y': (80, 120)},
    'qtd':      {'x': (0, 130),   'y': (155, 200)},
    'desconto': {'x': (110, 260), 'y': (220, 260)},
}


def _hwnd_janela_item() -> int | None:
    """Encontra a janela principal Ucom619 (Manutenção dos Itens da Ação Comercial)."""
    user32 = ctypes.windll.user32
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    achados: list[int] = []

    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(n)
        user32.GetWindowTextW(hwnd, buf, n)
        t = buf.value
        if "Ucom619" in t and "Manuten" in t:
            achados.append(hwnd)
        return True

    user32.EnumWindows(ENUMPROC(cb), 0)
    return achados[0] if achados else None


def _rect(hwnd: int) -> _RECT:
    r = _RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def _rect_zerado(r: _RECT) -> bool:
    return r.left == 0 and r.top == 0 and r.right == 0 and r.bottom == 0


def _campo_focado_rel() -> tuple[int, int] | None:
    """Retorna (cx, cy) da posição do CARET (cursor de texto) do campo ativo,
    relativo ao canto superior-esquerdo da janela Ucom619. None se não houver
    cursor (nenhum campo de texto em edição).

    Os campos da IABV não são janelas Win32 separadas (são desenhados dentro de
    uma única janela), então não dá para identificá-los pelo handle do foco. O
    caret, porém, fica posicionado dentro do campo ativo e muda de lugar de
    campo para campo — é o que usamos para identificar onde o cursor está."""
    janela = _hwnd_janela_item()
    if not janela:
        return None

    tid = _user32.GetWindowThreadProcessId(janela, None)
    gti = _GUITHREADINFO()
    gti.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if not _user32.GetGUIThreadInfo(tid, ctypes.byref(gti)):
        raise _SemPermissao()

    hcaret = gti.hwndCaret
    if not hcaret:
        return None  # nenhum campo de texto ativo (sem cursor piscando)

    # rcCaret está em coordenadas de cliente de hwndCaret; converte para tela.
    pt = _POINT(gti.rcCaret.left, gti.rcCaret.top)
    _user32.ClientToScreen(hcaret, ctypes.byref(pt))

    rj = _rect(janela)
    if _rect_zerado(rj):
        raise _SemPermissao()

    cx = pt.x - rj.left
    cy = pt.y - rj.top
    return (cx, cy)


def _debug_foco() -> str:
    """Dump dos valores crus usados na detecção, para diagnóstico."""
    u = _user32
    fg = u.GetForegroundWindow()
    nf = u.GetWindowTextLengthW(fg) + 1
    bf = ctypes.create_unicode_buffer(nf)
    u.GetWindowTextW(fg, bf, nf)

    janela = _hwnd_janela_item()
    tid = u.GetWindowThreadProcessId(janela, None) if janela else 0
    gti = _GUITHREADINFO()
    gti.cbSize = ctypes.sizeof(_GUITHREADINFO)
    ok = u.GetGUIThreadInfo(tid, ctypes.byref(gti)) if tid else 0
    hcaret = gti.hwndCaret
    rc = gti.rcCaret
    pt = _POINT(rc.left, rc.top)
    if hcaret:
        u.ClientToScreen(hcaret, ctypes.byref(pt))
    rj = _rect(janela) if janela else _RECT()
    return (f"fg='{bf.value[:18]}'\n"
            f"jan={janela} tid={tid} gti_ok={ok}\n"
            f"hcaret={hcaret}\n"
            f"rcCaret=({rc.left},{rc.top},{rc.right},{rc.bottom})\n"
            f"caret_tela=({pt.x},{pt.y})\n"
            f"rj=({rj.left},{rj.top},{rj.right},{rj.bottom})")


def _identificar_campo(rel: tuple[int, int] | None) -> str | None:
    """Classifica a posição relativa em 'codigo' | 'qtd' | 'desconto' | 'outro'.
    Retorna None se não foi possível ler o campo focado."""
    if rel is None:
        return None
    cx, cy = rel
    for nome, b in _CAMPOS.items():
        if b['x'][0] <= cx <= b['x'][1] and b['y'][0] <= cy <= b['y'][1]:
            return nome
    return 'outro'


def _diag() -> None:
    """Modo calibração: mostra continuamente o campo focado. Clique/Tab em
    cada campo do Ucom619 e anote os valores 'rel=' para ajustar _CAMPOS."""
    print("Modo diagnóstico de campos do Ucom619.")
    print("Deixe a janela Ucom619 aberta e em foco; clique/Tab em cada campo.")
    print("Anote o 'rel=' do código, da quantidade e do desconto. Ctrl+C para sair.\n")
    ultimo = None
    while True:
        try:
            rel = _campo_focado_rel()
            campo = _identificar_campo(rel)
            msg = f"rel={rel}  ->  {campo}"
        except _SemPermissao:
            msg = "SEM PERMISSAO: rode este script como Administrador (o IABV roda elevado)."
        if msg != ultimo:
            print(msg)
            ultimo = msg
        time.sleep(0.3)


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
            if not re.match(r'^(?:PU)?\d[\w-]*$', code):
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


def _frame_tela():
    """Captura a tela como thumbnail em tons de cinza, para comparação tolerante
    a micro-mudanças (ex.: cursor de texto piscando, relógio)."""
    img = pyautogui.screenshot().convert('L').resize((80, 45))
    return list(img.getdata())


def _telas_iguais(a, b, limiar_pixel: int = 24, limiar_frac: float = 0.01) -> bool:
    """Considera duas capturas iguais se diferirem em poucos pixels. Ignora
    micro-mudanças (caret piscando ocupa só alguns pixels da thumbnail)."""
    if a is None or b is None:
        return False
    diferentes = sum(1 for x, y in zip(a, b) if abs(x - y) > limiar_pixel)
    return diferentes / len(a) <= limiar_frac


def _aguardar_tela_estavel(timeout: float, intervalo: float = 0.4, n_estavel: int = 2) -> None:
    """Aguarda a tela parar de mudar. Avança assim que `n_estavel` capturas
    consecutivas forem (quase) idênticas, ou quando `timeout` for atingido."""
    anterior = None
    iguais = 0
    inicio = time.time()
    while time.time() - inicio < timeout:
        atual = _frame_tela()
        if _telas_iguais(atual, anterior):
            iguais += 1
            if iguais >= n_estavel:
                return
        else:
            iguais = 0
        anterior = atual
        time.sleep(intervalo)


def _fechar_popup_alerta_produto() -> None:
    """Fecha o popup Ucom434 'Existem alertas para este produto' pressionando Esc."""
    try:
        import ctypes
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

        hwnds: list[int] = []
        def cb(hwnd, _):
            n = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(n)
            user32.GetWindowTextW(hwnd, buf, n)
            if "Ucom434" in buf.value:
                hwnds.append(hwnd)
            return True
        user32.EnumWindows(ENUMPROC(cb), 0)

        for hwnd in hwnds:
            print("  [popup] alerta de produto detectado, fechando com Esc...")
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            pyautogui.press('escape')
            time.sleep(0.5)
    except Exception:
        pass


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
    """Aguarda após F5: fecha popup imediatamente e só avança quando a tela
    parar de mudar (sistema gravou o item). DELAY_APOS_F5 é o timeout máximo."""
    time.sleep(1.5)
    _fechar_popup_se_aberto()
    _aguardar_tela_estavel(timeout=DELAY_APOS_F5 - 1.5)


def _paste(text: str) -> None:
    """Cola texto via clipboard para garantir caracteres especiais (vírgula, etc.)."""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(DELAY_ETAPA)


# ---------------------------------------------------------------------------
# Preenchimento verificado de campos
#
# Duas checagens com papéis diferentes:
#   1. POSIÇÃO (caret) — só ESCOLHE entre as coordenadas alternativas de um
#      campo. É uma dica: nunca aborta sozinha, porque o caret nem sempre
#      existe (campo sem cursor piscando no momento da leitura).
#   2. CONTEÚDO — depois de colar, relê o campo pelo clipboard e compara com o
#      valor esperado. Esta sim manda: se não bater, o item é abortado ANTES
#      do F5, em vez de gravar errado.
# ---------------------------------------------------------------------------

_SENTINELA_CLIPBOARD = '\x00__campo_vazio__'

# _verificacao_posicao: usa o cursor para escolher entre as coordenadas
# alternativas de um campo. Deixe False para sempre usar a coordenada principal.
# _verificacao_conteudo: relê o campo depois de colar (desligue com
# --sem-conferencia se algum dia o sistema deixar de responder ao Ctrl+C).
_verificacao_posicao = True
_verificacao_conteudo = True


class _FalhaCampo(Exception):
    """Não foi possível garantir que o valor entrou no campo certo."""


def _origem_janela() -> tuple[int, int] | None:
    """Canto superior-esquerdo da janela Ucom619, ou None se indisponível."""
    janela = _hwnd_janela_item()
    if not janela:
        return None
    r = _rect(janela)
    if _rect_zerado(r):
        return None
    return (r.left, r.top)


def _caret_no_campo(coord: tuple[int, int]) -> bool | None:
    """True/False se o cursor está no campo da coordenada clicada.
    None quando não dá para saber (sem janela, sem permissão ou sem caret —
    vários campos só criam o cursor quando começam a ser editados)."""
    try:
        rel = _campo_focado_rel()
    except _SemPermissao:
        return None
    if rel is None:
        return None
    origem = _origem_janela()
    if origem is None:
        return None
    dx = rel[0] - (coord[0] - origem[0])
    dy = rel[1] - (coord[1] - origem[1])
    return abs(dy) <= TOL_CARET_Y and TOL_CARET_X[0] <= dx <= TOL_CARET_X[1]


def _focar_campo(candidatos: list[tuple[int, int]], nome: str) -> tuple[int, int]:
    """Clica no campo e devolve a coordenada usada.

    Com mais de uma coordenada possível, usa o cursor para escolher qual delas
    é o campo de verdade no layout atual. Nunca levanta erro: se a checagem de
    posição não estiver disponível ou não confirmar nenhuma, fica na primeira
    coordenada e deixa a conferência de conteúdo decidir."""
    if len(candidatos) == 1 or not _verificacao_posicao:
        coord = candidatos[0]
        pyautogui.click(coord[0], coord[1])
        time.sleep(0.4)
        return coord

    for coord in candidatos:
        pyautogui.click(coord[0], coord[1])
        time.sleep(0.4)
        if _caret_no_campo(coord):
            return coord

    # Nenhuma confirmou (cursor indisponível ou fora das tolerâncias): volta
    # para a principal — a releitura do valor é quem vai reprovar, se for o caso.
    coord = candidatos[0]
    pyautogui.click(coord[0], coord[1])
    time.sleep(0.4)
    return coord


def _limpar_campo() -> None:
    """Apaga o conteúdo do campo focado. Usa seleção por Home/End em vez de
    Ctrl+A, que nesses campos legados não seleciona nada — e fazia o valor novo
    ser concatenado ao antigo (origem dos valores 'aleatórios' no desconto)."""
    pyautogui.press('end')
    pyautogui.hotkey('shift', 'home')
    time.sleep(0.15)
    pyautogui.press('delete')
    time.sleep(0.15)
    # Se o 'end' não tiver funcionado, limpa também o que sobrou à direita.
    pyautogui.hotkey('shift', 'end')
    time.sleep(0.15)
    pyautogui.press('delete')
    time.sleep(0.15)


def _ler_campo() -> str | None:
    """Devolve o conteúdo do campo focado via seleção + clipboard.
    None quando o app não devolveu nada (campo vazio ou Ctrl+C sem efeito)."""
    pyperclip.copy(_SENTINELA_CLIPBOARD)
    pyautogui.press('home')
    pyautogui.hotkey('shift', 'end')
    time.sleep(0.15)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.4)
    lido = pyperclip.paste()
    # Desfaz a seleção: qualquer tecla enviada depois (Enter, F5) com o texto
    # selecionado poderia apagar o valor que acabamos de conferir.
    pyautogui.press('end')
    time.sleep(0.1)
    if lido == _SENTINELA_CLIPBOARD:
        return None
    return lido.strip()


def _como_numero(s: str) -> float | None:
    limpo = re.sub(r'[^\d,.]', '', s)
    if ',' in limpo:
        limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return None


def _valores_batem(esperado: str, lido: str) -> bool:
    """Compara tolerando a formatação do sistema (66,50 == 66,5 == 66.50,
    20 == 20,00)."""
    if not lido:
        return False
    if lido == esperado:
        return True
    ne, nl = _como_numero(esperado), _como_numero(lido)
    if ne is not None and nl is not None:
        return abs(ne - nl) < 0.005
    return lido.upper().startswith(esperado.upper())


def _preencher_campo(candidatos: list[tuple[int, int]], valor: str, nome: str,
                     tentativas: int = 3) -> None:
    """Foca o campo, limpa, cola o valor e confirma que foi digitado ali."""
    ultimo_lido = None
    for tentativa in range(1, tentativas + 1):
        _focar_campo(candidatos, nome)
        _limpar_campo()
        _paste(valor)

        if not _verificacao_conteudo:
            return

        lido = _ler_campo()
        if lido is not None and _valores_batem(valor, lido):
            return

        # Leitura vazia = ou o clique não pegou o campo, ou a colagem não
        # surtiu efeito. Nos dois casos o valor não está lá: vale repetir.
        ultimo_lido = lido if lido else '(vazio)'
        print(f"  [tentativa {tentativa}/{tentativas}] {nome}: esperado '{valor}', "
              f"campo está '{ultimo_lido}'")
        time.sleep(0.5)

    raise _FalhaCampo(
        f"campo '{nome}': esperado '{valor}', mas ficou '{ultimo_lido}'")


def _process_item(item: dict, index: int, total: int) -> None:
    code = item['code']
    qty = item['qty']
    skip_discount = item['skip_discount']
    discount = item['discount']

    desc_info = "sem desconto (**)" if skip_discount else f"desconto: {discount}%"
    print(f"[{index}/{total}] Código: {code} | Qtd: {qty} | {desc_info}")

    # 1. Código do produto: clica no campo, cola e confirma com Enter
    _preencher_campo(CAMPOS_CODIGO, code, 'código')
    pyautogui.press('enter')
    time.sleep(DELAY_ETAPA)
    _fechar_popup_alerta_produto()

    # 2. Quantidade: clica direto no campo de Qtd e digita
    _preencher_campo(CAMPOS_QTD, qty, 'quantidade')

    # 3. Desconto: clica direto no campo de % e digita (só o valor numérico)
    if not skip_discount:
        _preencher_campo(CAMPOS_DESCONTO, discount, 'desconto')
        _fechar_popup_se_aberto()

    # 4. Grava o item
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

            if not re.match(r'^(?:PU)?\d[\w-]*$', code):
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

    # Código do produto: clica no campo, cola e confirma com Enter
    _preencher_campo(CAMPOS_CODIGO, code, 'código')
    pyautogui.press('enter')
    time.sleep(DELAY_ETAPA)
    _fechar_popup_alerta_produto()

    if is_new:
        # Item novo: mesmo fluxo do criar pedido (clica em cada campo)
        _preencher_campo(CAMPOS_QTD, item['qty'], 'quantidade')
        if not item['skip_discount']:
            _preencher_campo(CAMPOS_DESCONTO, item['discount'], 'desconto')
            _fechar_popup_se_aberto()
    else:
        # Item existente: no lugar do segundo Enter, clica para fechar o popup
        # que sempre aparece ao editar; depois clica só nos campos a alterar.
        pyautogui.click(*POPUP_EDITAR)
        time.sleep(DELAY_ETAPA)

        if item['has_qty']:
            _preencher_campo(CAMPOS_QTD, item['qty'], 'quantidade')
        if item['has_discount']:
            _preencher_campo(CAMPOS_DESCONTO, item['discount'], 'desconto')
            _fechar_popup_se_aberto()

    # Grava o item
    pyautogui.press('f5')
    _aguardar_apos_f5()


def main() -> None:
    global _verificacao_conteudo

    if '--diag' in sys.argv:
        _diag()
        return

    if '--sem-conferencia' in sys.argv:
        _verificacao_conteudo = False
        print("Conferência de conteúdo DESLIGADA (--sem-conferencia).")

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
        try:
            if editar_mode:
                _process_item_editar(item, i, len(items))
            else:
                _process_item(item, i, len(items))
        except _FalhaCampo as e:
            # Para antes do F5: melhor parar do que gravar o item errado.
            print(f"\nPARADO no item {i}/{len(items)} (código {item['code']}): {e}")
            print("Este item NÃO foi gravado (o F5 não chegou a ser pressionado).")
            print("Causas prováveis, nesta ordem:")
            print("  1. A janela do IABV não está maximizada ou perdeu o foco.")
            print("  2. As coordenadas dos campos mudaram — recalibre com: "
                  "python calibrar_campos.py")
            print("  3. O sistema parou de responder ao Ctrl+C nos campos — nesse")
            print("     caso rode com --sem-conferencia (perde a checagem de valores).")
            sys.exit(1)

    print("\nAutomação concluída!")


if __name__ == "__main__":
    main()
