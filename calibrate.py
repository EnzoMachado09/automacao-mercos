from __future__ import annotations

from pathlib import Path
import tkinter as tk

import pyautogui


def main() -> int:
    root = tk.Tk()
    root.title("Calibrador de Coordenadas")
    root.attributes("topmost", True)
    root.resizable(False, False)

    coord_var = tk.StringVar(value="Posicione o mouse sobre o ponto desejado")
    status_var = tk.StringVar(value="Clique em Capturar ou pressione Enter para salvar a posicao atual.")

    def current_position() -> tuple[int, int]:
        point = pyautogui.position()
        return point.x, point.y

    def refresh() -> None:
        x, y = current_position()
        coord_var.set(f"X: {x}    Y: {y}")
        root.after(100, refresh)

    def capture_position(event: object | None = None) -> None:
        x, y = current_position()
        coord_var.set(f"Capturado: [{x}, {y}]")
        status_var.set("Copie essa posicao para o arquivo de configuracao.")
        root.clipboard_clear()
        root.clipboard_append(f"[{x}, {y}]")
        root.update()

    def save_screenshot() -> None:
        screenshots_dir = Path.cwd() / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        file_path = screenshots_dir / "calibracao_tela.png"
        image = pyautogui.screenshot()
        image.save(file_path)
        status_var.set(f"Screenshot salvo em {file_path}")

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack()

    tk.Label(frame, text="Calibrador de Coordenadas", font=("Segoe UI", 12, "bold")).pack(pady=(0, 8))
    tk.Label(frame, textvariable=coord_var, font=("Consolas", 14)).pack(pady=(0, 8))
    tk.Label(frame, textvariable=status_var, wraplength=360, justify="left").pack(pady=(0, 12))

    button_row = tk.Frame(frame)
    button_row.pack(fill="x")

    tk.Button(button_row, text="Capturar", width=14, command=capture_position).pack(side="left", padx=(0, 8))
    tk.Button(button_row, text="Salvar Screenshot", width=16, command=save_screenshot).pack(side="left", padx=(0, 8))
    tk.Button(button_row, text="Sair", width=10, command=root.destroy).pack(side="left")

    root.bind("<Return>", capture_position)
    root.bind("<Escape>", lambda event: root.destroy())

    refresh()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
