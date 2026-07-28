#!/usr/bin/env python3
"""
Calibrador de Campos do Ucom619 (interface gráfica)

Mostra em tempo real:
  - qual campo do Ucom619 está com FOCO (código / qtd / desconto / outro)
  - a posição relativa (rel) desse campo dentro da janela Ucom619
  - a posição absoluta do mouse (fallback, como o calibrador antigo)

Como usar:
  1. Abra a tela Ucom619 (Manutenção dos Itens da Ação Comercial) com um item.
  2. Rode este script:  python calibrar_campos.py
  3. Esta janelinha fica SEMPRE no topo. Clique (ou Tab) em cada campo do
     Ucom619 — o "Campo focado" e o "rel" abaixo se atualizam sozinhos.
  4. Com o campo do Ucom619 focado, aperte F2 para COPIAR o rel daquele campo
     sem perder o foco (hotkey global). O botão também copia.
  5. Anote o rel do CÓDIGO, da QUANTIDADE e do DESCONTO e ajuste _CAMPOS no
     main.py (ou me mande os valores).
"""

from __future__ import annotations

import ctypes
import tkinter as tk

VK_F2 = 0x71  # tecla F2 (hotkey global para copiar o rel)

try:
    import pyautogui
except ModuleNotFoundError:
    print("Erro: 'pyautogui' não está instalado no ambiente ativo.")
    print(r"Instale com: .\.venv\Scripts\python.exe -m pip install pyautogui")
    raise SystemExit(1)

# Reaproveita a lógica de detecção de campo do main.py
from main import (
    _campo_focado_rel,
    _identificar_campo,
    _hwnd_janela_item,
    _debug_foco,
    _SemPermissao,
)


def main() -> int:
    root = tk.Tk()
    root.title("Calibrador de Campos - Ucom619")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    janela_var = tk.StringVar(value="Procurando janela Ucom619...")
    campo_var = tk.StringVar(value="Campo focado: -")
    rel_var = tk.StringVar(value="rel: -")
    mouse_var = tk.StringVar(value="Mouse: -")
    debug_var = tk.StringVar(value="debug...")
    status_var = tk.StringVar(value="Clique em cada campo do Ucom619.")

    ultimo_rel: list[tuple[int, int] | None] = [None]
    hotkey_baixo = [False]  # estado anterior da tecla, para detectar a borda

    def refresh() -> None:
        achou_janela = _hwnd_janela_item() is not None
        janela_var.set(
            "Janela Ucom619: ENCONTRADA" if achou_janela
            else "Janela Ucom619: NÃO encontrada (abra a tela do item)"
        )

        try:
            rel = _campo_focado_rel()
            ultimo_rel[0] = rel
            campo = _identificar_campo(rel)
            campo_var.set(f"Campo focado: {campo}")
            rel_var.set(f"rel: {rel}")
        except _SemPermissao:
            ultimo_rel[0] = None
            campo_var.set("Campo focado: SEM PERMISSAO")
            rel_var.set("Feche e rode como ADMINISTRADOR")

        p = pyautogui.position()
        mouse_var.set(f"Mouse: X={p.x}  Y={p.y}")

        try:
            debug_var.set(_debug_foco())
        except Exception as e:
            debug_var.set(f"debug erro: {e}")

        # Hotkey global: F2 copia o rel atual sem tirar o foco do Ucom619.
        # Detecta a borda (tecla acabou de ser pressionada).
        pressionada = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F2) & 0x8000)
        if pressionada and not hotkey_baixo[0]:
            copiar_rel()
        hotkey_baixo[0] = pressionada

        root.after(80, refresh)

    def copiar_rel(event: object | None = None) -> None:
        # Captura a posição ABSOLUTA do mouse (sempre confiável, não depende
        # de foco). É o que usamos para clicar direto em cada campo.
        p = pyautogui.position()
        root.clipboard_clear()
        root.clipboard_append(f"[{p.x}, {p.y}]")
        root.update()
        status_var.set(f"Copiado mouse: [{p.x}, {p.y}]")

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack()

    tk.Label(frame, text="Calibrador de Campos - Ucom619",
             font=("Segoe UI", 12, "bold")).pack(pady=(0, 8))
    tk.Label(frame, textvariable=janela_var, font=("Segoe UI", 9)).pack(anchor="w")
    tk.Label(frame, textvariable=campo_var, font=("Consolas", 16)).pack(pady=(8, 0))
    tk.Label(frame, textvariable=rel_var, font=("Consolas", 14)).pack()
    tk.Label(frame, textvariable=mouse_var, font=("Consolas", 11)).pack(pady=(4, 8))
    tk.Label(frame, textvariable=status_var, wraplength=340,
             justify="left").pack(pady=(0, 12))

    tk.Label(frame, textvariable=debug_var, font=("Consolas", 9),
             justify="left", fg="#555").pack(anchor="w", pady=(0, 8))

    tk.Label(frame, text="Posicione o mouse sobre o campo e aperte F2 para copiar X,Y",
             font=("Segoe UI", 9, "italic")).pack(pady=(0, 8))

    button_row = tk.Frame(frame)
    button_row.pack(fill="x")
    tk.Button(button_row, text="Copiar X,Y (F2)", width=14,
              command=copiar_rel).pack(side="left", padx=(0, 8))
    tk.Button(button_row, text="Sair", width=10,
              command=root.destroy).pack(side="left")

    root.bind("<Return>", copiar_rel)
    root.bind("<Escape>", lambda event: root.destroy())

    refresh()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
