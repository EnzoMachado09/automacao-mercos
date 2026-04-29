#!/usr/bin/env python3
"""
Hotkey Launcher para Automação Mercos
Tecla F6: iniciar/parar etapa selecionada
Tecla ESC: fechar a aplicação
"""

import subprocess
import sys
import threading
from pathlib import Path
from tkinter import Tk, Label, Button, Frame, Text, Scrollbar, Entry, StringVar, Radiobutton
from tkinter import font as tkFont

try:
    import keyboard
except ImportError:
    print("Biblioteca 'keyboard' nao instalada.")
    print("Execute: python -m pip install keyboard")
    sys.exit(1)


class HotKeyLauncher:
    def __init__(self):
        self.process = None
        self.is_running = False

        self.root = Tk()
        self.root.title("Automacao Mercos - Hotkey Launcher")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        self.etapa_selecionada = StringVar(value="etapa1")
        self.max_orders = StringVar(value="1")

        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        title_font = tkFont.Font(family="Arial", size=14, weight="bold")
        status_font = tkFont.Font(family="Arial", size=12)
        info_font = tkFont.Font(family="Courier", size=9)

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title_label = Label(
            main_frame,
            text="Automacao Mercos",
            font=title_font,
            bg="#f0f0f0",
            fg="#333333",
        )
        title_label.pack(pady=(10, 10))

        self.status_label = Label(
            main_frame,
            text="PARADA",
            font=status_font,
            bg="#ffcccc",
            fg="#990000",
            relief="solid",
            borderwidth=2,
            padx=20,
            pady=10,
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        info_frame = Frame(main_frame, bg="#f0f0f0")
        info_frame.pack(fill="x", pady=(0, 10))

        info1 = Label(
            info_frame,
            text="F6: Iniciar/Parar etapa selecionada | ESC: Fechar",
            font=info_font,
            bg="#f0f0f0",
            fg="#333333",
        )
        info1.pack(anchor="w")

        etapa_frame = Frame(main_frame, bg="#fff3e0", relief="solid", borderwidth=1)
        etapa_frame.pack(fill="x", pady=(0, 10), padx=0)

        etapa_label = Label(
            etapa_frame,
            text="Selecione a Etapa",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#fff3e0",
            fg="#e65100",
        )
        etapa_label.pack(anchor="w", padx=10, pady=(5, 0))

        etapa_radio_frame = Frame(etapa_frame, bg="#fff3e0")
        etapa_radio_frame.pack(fill="x", padx=10, pady=5)

        self.rb1 = Radiobutton(
            etapa_radio_frame,
            text="Etapa 1: Exportar pedidos (PDF)",
            variable=self.etapa_selecionada,
            value="etapa1",
            bg="#fff3e0",
            fg="#333333",
            font=info_font,
        )
        self.rb1.pack(anchor="w")

        self.rb2 = Radiobutton(
            etapa_radio_frame,
            text="Etapa 2: Extrair dados Excel (openpyxl)",
            variable=self.etapa_selecionada,
            value="etapa2",
            bg="#fff3e0",
            fg="#333333",
            font=info_font,
        )
        self.rb2.pack(anchor="w")

        self.rb3 = Radiobutton(
            etapa_radio_frame,
            text="Etapa 3: Criar pedidos no Mercos Web",
            variable=self.etapa_selecionada,
            value="etapa3",
            bg="#fff3e0",
            fg="#333333",
            font=info_font,
        )
        self.rb3.pack(anchor="w")

        config_frame = Frame(main_frame, bg="#e8f5e9", relief="solid", borderwidth=1)
        config_frame.pack(fill="x", pady=(0, 10), padx=0)

        config_label = Label(
            config_frame,
            text="Configuracao (Etapa 1)",
            font=tkFont.Font(family="Arial", size=9, weight="bold"),
            bg="#e8f5e9",
            fg="#1b5e20",
        )
        config_label.pack(anchor="w", padx=10, pady=(5, 0))

        max_orders_frame = Frame(config_frame, bg="#e8f5e9")
        max_orders_frame.pack(fill="x", padx=10, pady=5)

        max_orders_label = Label(
            max_orders_frame,
            text="Quantos pedidos processar?",
            font=info_font,
            bg="#e8f5e9",
            fg="#1b5e20",
        )
        max_orders_label.pack(side="left", padx=(0, 10))

        self.max_orders_entry = Entry(
            max_orders_frame,
            textvariable=self.max_orders,
            font=info_font,
            width=8,
            justify="center",
        )
        self.max_orders_entry.pack(side="left")

        log_label = Label(
            main_frame,
            text="Saida da automacao:",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#f0f0f0",
            fg="#333333",
        )
        log_label.pack(anchor="w", pady=(5, 0))

        log_frame = Frame(main_frame, bg="white", relief="solid", borderwidth=1)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        scrollbar = Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = Text(
            log_frame,
            font=info_font,
            bg="white",
            fg="#333333",
            yscrollcommand=scrollbar.set,
            state="disabled",
            height=12,
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        button_frame = Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")

        self.toggle_button = Button(
            button_frame,
            text="INICIAR ETAPA SELECIONADA",
            command=self.toggle_automation,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=8,
            relief="raised",
            borderwidth=2,
        )
        self.toggle_button.pack(side="left", expand=True, padx=5)

        close_button = Button(
            button_frame,
            text="FECHAR",
            command=self.close_app,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=8,
            relief="raised",
            borderwidth=2,
        )
        close_button.pack(side="right", expand=True, padx=5)

        keyboard.add_hotkey("f6", self.toggle_automation)
        keyboard.add_hotkey("esc", self.close_app)

        self.log("Launcher iniciado")
        self.log("F6: Iniciar/Parar etapa selecionada")
        self.log("ESC: Fechar")

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

        etapa = self.etapa_selecionada.get()

        if etapa == "etapa1":
            try:
                max_orders_val = int(self.max_orders.get())
                if max_orders_val <= 0:
                    self.log("Erro: max orders deve ser maior que 0")
                    return
            except ValueError:
                self.log("Erro: max orders invalido")
                return

        self.is_running = True
        self._set_running_ui(etapa)

        thread = threading.Thread(target=self._run_selected_stage, args=(etapa,), daemon=True)
        thread.start()

    def _set_running_ui(self, etapa: str):
        labels = {"etapa1": "ETAPA 1", "etapa2": "ETAPA 2", "etapa3": "ETAPA 3"}
        etapa_label = labels.get(etapa, etapa.upper())
        self.status_label.config(text=f"EXECUTANDO {etapa_label}", bg="#fff3cd", fg="#8a6d3b")
        self.toggle_button.config(text="PARAR", bg="#ff9800")
        self.rb1.config(state="disabled")
        self.rb2.config(state="disabled")
        self.rb3.config(state="disabled")
        self.max_orders_entry.config(state="disabled")
        self.root.update()

    def _set_idle_ui(self):
        self.status_label.config(text="PARADA", bg="#ffcccc", fg="#990000")
        self.toggle_button.config(text="INICIAR ETAPA SELECIONADA", bg="#2196F3")
        self.rb1.config(state="normal")
        self.rb2.config(state="normal")
        self.rb3.config(state="normal")
        self.max_orders_entry.config(state="normal")
        self.root.update()

    def _build_command(self, etapa: str):
        python_exe = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
        if not python_exe.exists():
            raise FileNotFoundError(f"Python nao encontrado em: {python_exe}")

        if etapa == "etapa1":
            output_dir = Path(__file__).parent / "out"
            output_dir.mkdir(exist_ok=True)
            max_orders_val = int(self.max_orders.get())
            return [
                str(python_exe),
                "-m",
                "src.main",
                "--output-dir",
                str(output_dir),
                "--max-orders",
                str(max_orders_val),
            ]

        if etapa == "etapa2":
            return [str(python_exe), "main_etapa2.py"]

        return [str(python_exe), "main_etapa3.py"]

    def _run_selected_stage(self, etapa: str):
        try:
            cmd = self._build_command(etapa)
            self.log(f"Executando: {' '.join(cmd)}")

            # stderr vai para stdout para evitar deadlock por buffer.
            self.process = subprocess.Popen(
                cmd,
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
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
