#!/usr/bin/env python3
"""
Hotkey Launcher para Automações
Tecla F6: iniciar/parar etapa selecionada
Tecla ESC: fechar a aplicação

Cada automação em automacoes/<nome>/manifest.json define suas etapas.
"""

import json
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import Tk, Label, Button, Frame, Text, Scrollbar, Entry, StringVar, Radiobutton
from tkinter import font as tkFont
from tkinter import ttk

try:
    import keyboard
except ImportError:
    print("Biblioteca 'keyboard' nao instalada.")
    print("Execute: python -m pip install keyboard")
    sys.exit(1)

ROOT_DIR = Path(__file__).parent
AUTOMACOES_DIR = ROOT_DIR / "automacoes"


def _listar_automacoes() -> list[str]:
    if not AUTOMACOES_DIR.exists():
        return []
    return sorted(
        p.name for p in AUTOMACOES_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "manifest.json").exists()
    )


def _carregar_manifest(automacao: str) -> list[dict]:
    manifest_path = AUTOMACOES_DIR / automacao / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("etapas", [])
    except Exception:
        return []


def _nome_display(automacao: str) -> str:
    manifest_path = AUTOMACOES_DIR / automacao / "manifest.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data.get("nome", automacao)
    except Exception:
        return automacao


class HotKeyLauncher:
    def __init__(self):
        self.process = None
        self.is_running = False
        self.radio_buttons: list[Radiobutton] = []
        self.etapas_manifest: list[dict] = []

        self.root = Tk()
        self.root.title("Automacoes - Launcher")
        self.root.geometry("700x620")
        self.root.resizable(True, True)

        self.etapa_selecionada = StringVar(value="etapa1")
        self.max_orders = StringVar(value="1")

        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        title_font = tkFont.Font(family="Arial", size=14, weight="bold")
        status_font = tkFont.Font(family="Arial", size=12)
        self.info_font = tkFont.Font(family="Courier", size=9)

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        Label(
            main_frame, text="Automacoes - Launcher",
            font=title_font, bg="#f0f0f0", fg="#333333",
        ).pack(pady=(10, 5))

        # --- Seleção de automação ---
        automacao_frame = Frame(main_frame, bg="#f0f0f0")
        automacao_frame.pack(fill="x", pady=(0, 8))

        Label(automacao_frame, text="Automacao:", font=self.info_font, bg="#f0f0f0", fg="#333333").pack(side="left", padx=(0, 8))

        automacoes = _listar_automacoes()
        nomes_display = [_nome_display(a) for a in automacoes]
        self._automacoes_ids = automacoes  # ids internos (nome de pasta)
        self._automacoes_nomes = nomes_display

        self.automacao_selecionada = StringVar(value=nomes_display[0] if nomes_display else "")
        self.automacao_combo = ttk.Combobox(
            automacao_frame,
            textvariable=self.automacao_selecionada,
            values=nomes_display,
            state="readonly",
            width=22,
            font=self.info_font,
        )
        self.automacao_combo.pack(side="left")
        self.automacao_combo.bind("<<ComboboxSelected>>", lambda _: self._reconstruir_etapas())

        # --- Status ---
        self.status_label = Label(
            main_frame, text="PARADA", font=status_font,
            bg="#ffcccc", fg="#990000", relief="solid", borderwidth=2, padx=20, pady=10,
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        Label(
            main_frame,
            text="F6: Iniciar/Parar etapa selecionada | ESC: Fechar",
            font=self.info_font, bg="#f0f0f0", fg="#333333",
        ).pack(anchor="w", pady=(0, 8))

        # --- Etapas (dinâmico) ---
        etapa_outer = Frame(main_frame, bg="#fff3e0", relief="solid", borderwidth=1)
        etapa_outer.pack(fill="x", pady=(0, 10))

        Label(
            etapa_outer, text="Selecione a Etapa",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#fff3e0", fg="#e65100",
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.etapa_radio_frame = Frame(etapa_outer, bg="#fff3e0")
        self.etapa_radio_frame.pack(fill="x", padx=10, pady=5)

        # --- Campo max orders (visível só quando necessário) ---
        self.config_frame = Frame(main_frame, bg="#e8f5e9", relief="solid", borderwidth=1)
        # empacotado/desempacotado dinamicamente em _reconstruir_etapas

        Label(
            self.config_frame, text="Configuracao (Etapa 1)",
            font=tkFont.Font(family="Arial", size=9, weight="bold"),
            bg="#e8f5e9", fg="#1b5e20",
        ).pack(anchor="w", padx=10, pady=(5, 0))

        max_frame = Frame(self.config_frame, bg="#e8f5e9")
        max_frame.pack(fill="x", padx=10, pady=5)

        Label(max_frame, text="Quantos pedidos processar?", font=self.info_font, bg="#e8f5e9", fg="#1b5e20").pack(side="left", padx=(0, 10))

        self.max_orders_entry = Entry(max_frame, textvariable=self.max_orders, font=self.info_font, width=8, justify="center")
        self.max_orders_entry.pack(side="left")

        # --- Log ---
        Label(
            main_frame, text="Saida da automacao:",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#f0f0f0", fg="#333333",
        ).pack(anchor="w", pady=(5, 0))

        log_frame = Frame(main_frame, bg="white", relief="solid", borderwidth=1)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        scrollbar = Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = Text(
            log_frame, font=self.info_font, bg="white", fg="#333333",
            yscrollcommand=scrollbar.set, state="disabled", height=12,
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # --- Botões ---
        button_frame = Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")

        self.toggle_button = Button(
            button_frame, text="INICIAR ETAPA SELECIONADA",
            command=self.toggle_automation,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#2196F3", fg="white", padx=20, pady=8, relief="raised", borderwidth=2,
        )
        self.toggle_button.pack(side="left", expand=True, padx=5)

        Button(
            button_frame, text="FECHAR", command=self.close_app,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#f44336", fg="white", padx=20, pady=8, relief="raised", borderwidth=2,
        ).pack(side="right", expand=True, padx=5)

        keyboard.add_hotkey("f6", self.toggle_automation)
        keyboard.add_hotkey("esc", self.close_app)

        # Inicializar etapas da automação padrão
        self._reconstruir_etapas()

        self.log("Launcher iniciado")
        self.log("F6: Iniciar/Parar | ESC: Fechar")

    # ------------------------------------------------------------------
    # Manifest / etapas dinâmicas
    # ------------------------------------------------------------------

    def _automacao_id(self) -> str:
        nome_display = self.automacao_selecionada.get()
        try:
            idx = self._automacoes_nomes.index(nome_display)
            return self._automacoes_ids[idx]
        except (ValueError, IndexError):
            return nome_display

    def _reconstruir_etapas(self) -> None:
        automacao = self._automacao_id()
        self.etapas_manifest = _carregar_manifest(automacao)

        # Remove radio buttons antigos
        for rb in self.radio_buttons:
            rb.destroy()
        self.radio_buttons.clear()

        if not self.etapas_manifest:
            self.etapas_manifest = [{"id": "etapa1", "label": "Executar", "mode": "script", "entry": "main.py"}]

        # Seleciona primeira etapa por padrão
        self.etapa_selecionada.set(self.etapas_manifest[0]["id"])

        for etapa in self.etapas_manifest:
            rb = Radiobutton(
                self.etapa_radio_frame,
                text=etapa.get("label", etapa["id"]),
                variable=self.etapa_selecionada,
                value=etapa["id"],
                bg="#fff3e0", fg="#333333",
                font=self.info_font,
                command=self._atualizar_config_frame,
            )
            rb.pack(anchor="w")
            self.radio_buttons.append(rb)

        self._atualizar_config_frame()

    def _etapa_atual(self) -> dict | None:
        etapa_id = self.etapa_selecionada.get()
        for e in self.etapas_manifest:
            if e["id"] == etapa_id:
                return e
        return None

    def _atualizar_config_frame(self) -> None:
        etapa = self._etapa_atual()
        needs_max = etapa.get("needs_max_orders", False) if etapa else False
        if needs_max:
            self.config_frame.pack(fill="x", pady=(0, 10), before=self.log_text.master)
        else:
            self.config_frame.pack_forget()

    # ------------------------------------------------------------------
    # Controle de processo
    # ------------------------------------------------------------------

    def log(self, message: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update()
        print(message)

    def toggle_automation(self):
        if not self.is_running:
            self.start_automation()
        else:
            self.stop_automation()

    def start_automation(self):
        if self.is_running:
            self.log("Automacao ja em execucao")
            return

        etapa = self._etapa_atual()
        if etapa and etapa.get("needs_max_orders"):
            try:
                val = int(self.max_orders.get())
                if val <= 0:
                    self.log("Erro: max orders deve ser maior que 0")
                    return
            except ValueError:
                self.log("Erro: max orders invalido")
                return

        self.is_running = True
        self._set_running_ui()

        thread = threading.Thread(target=self._run_selected_stage, daemon=True)
        thread.start()

    def _set_running_ui(self):
        etapa = self._etapa_atual()
        label = etapa.get("label", "ETAPA").upper() if etapa else "ETAPA"
        self.status_label.config(text=f"EXECUTANDO: {label}", bg="#fff3cd", fg="#8a6d3b")
        self.toggle_button.config(text="PARAR", bg="#ff9800")
        for rb in self.radio_buttons:
            rb.config(state="disabled")
        self.max_orders_entry.config(state="disabled")
        self.automacao_combo.config(state="disabled")
        self.root.update()

    def _set_idle_ui(self):
        self.status_label.config(text="PARADA", bg="#ffcccc", fg="#990000")
        self.toggle_button.config(text="INICIAR ETAPA SELECIONADA", bg="#2196F3")
        for rb in self.radio_buttons:
            rb.config(state="normal")
        self.max_orders_entry.config(state="normal")
        self.automacao_combo.config(state="readonly")
        self.root.update()

    def _build_command(self) -> list[str]:
        python_exe = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
        if not python_exe.exists():
            raise FileNotFoundError(f"Python nao encontrado em: {python_exe}")

        automacao = self._automacao_id()
        automacao_dir = AUTOMACOES_DIR / automacao
        etapa = self._etapa_atual()
        if not etapa:
            raise ValueError("Nenhuma etapa selecionada")

        mode = etapa.get("mode", "script")
        entry = etapa["entry"]

        if mode == "module":
            # ex: python -m automacoes.mercos.src.main --output-dir ... --max-orders ...
            output_dir = automacao_dir / "out"
            output_dir.mkdir(parents=True, exist_ok=True)
            cmd = [str(python_exe), "-m", f"automacoes.{automacao}.{entry}"]
            if etapa.get("needs_max_orders"):
                cmd += ["--output-dir", str(output_dir), "--max-orders", self.max_orders.get()]
            return cmd

        # mode == "script"
        cmd = [str(python_exe), str(automacao_dir / entry)]
        if etapa.get("args"):
            cmd += [str(a) for a in etapa["args"]]
        return cmd

    def _run_selected_stage(self):
        try:
            cmd = self._build_command()
            self.log(f"Executando: {' '.join(cmd)}")

            import os
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"

            self.process = subprocess.Popen(
                cmd,
                cwd=ROOT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=env,
            )

            self.log(f"Processo iniciado (PID: {self.process.pid})")

            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.log(line.rstrip())

            self.process.wait()

            if self.process.returncode == 0:
                self.log("Etapa concluida com sucesso")
            else:
                self.log(f"Etapa finalizou com codigo: {self.process.returncode}")

        except Exception as e:
            self.log(f"Erro ao executar etapa: {e}")

        finally:
            self.is_running = False
            self.process = None
            self._set_idle_ui()
            self.log("=" * 50)

    def stop_automation(self):
        if not self.process:
            self.log("Nenhum processo em execucao")
            return
        try:
            self.log(f"Parando processo (PID: {self.process.pid})...")
            self.process.terminate()
            self.process.wait(timeout=5)
            self.log("Processo parado")
        except Exception:
            try:
                self.process.kill()
                self.log("Processo finalizado forcadamente")
            except Exception as e:
                self.log(f"Erro ao parar processo: {e}")

    def close_app(self):
        if self.is_running:
            self.stop_automation()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()
        print("Aplicacao encerrada")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.root.mainloop()


def main():
    launcher = HotKeyLauncher()
    launcher.run()


if __name__ == "__main__":
    main()
