#!/usr/bin/env python3
"""
Hotkey Launcher para Automação Mercos
Tecla F6: iniciar automação Etapa 1 (PDF export)
Tecla F7: iniciar automação Etapa 2 (Excel extraction)
Tecla ESC: fechar a aplicação
"""

import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import Tk, Label, Button, Frame, Text, Scrollbar, Entry, StringVar, Radiobutton
from tkinter import font as tkFont

try:
    import keyboard
except ImportError:
    print("❌ Biblioteca 'keyboard' não instalada.")
    print("Execute: python -m pip install keyboard")
    sys.exit(1)


class HotKeyLauncher:
    def __init__(self):
        self.process = None
        self.is_running = False
        self.root = Tk()
        self.root.title("Automação Mercos - Hotkey Launcher")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Variáveis
        self.max_orders = StringVar(value="1")  # Valor padrão: 1 pedido
        self.etapa_selecionada = StringVar(value="etapa1")  # Padrão: Etapa 1
        
        # Tenta colocar a janela sempre no topo
        try:
            self.root.attributes("-topmost", True)
        except:
            pass
        
        # Define estilos
        title_font = tkFont.Font(family="Arial", size=14, weight="bold")
        status_font = tkFont.Font(family="Arial", size=12)
        info_font = tkFont.Font(family="Courier", size=9)
        
        # Frame principal
        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Título
        title_label = Label(
            main_frame, 
            text="🤖 Automação Mercos",
            font=title_font,
            bg="#f0f0f0",
            fg="#333333"
        )
        title_label.pack(pady=(10, 10))
        
        # Status
        self.status_label = Label(
            main_frame,
            text="⏹️  PARADA",
            font=status_font,
            bg="#ffcccc",
            fg="#990000",
            relief="solid",
            borderwidth=2,
            padx=20,
            pady=10
        )
        self.status_label.pack(fill="x", pady=(0, 10))
        
        # Instruções
        info_frame = Frame(main_frame, bg="#f0f0f0")
        info_frame.pack(fill="x", pady=(0, 10))
        
        info1 = Label(
            info_frame,
            text="🟢 F6: Etapa 1 (PDF)  |  🟡 F7: Etapa 2 (Excel)  |  🔴 ESC: Fechar",
            font=info_font,
            bg="#f0f0f0",
            fg="#333333"
        )
        info1.pack(anchor="w")
        
        # ============================================================================
        # SELEÇÃO DE ETAPA
        # ============================================================================
        
        etapa_frame = Frame(main_frame, bg="#fff3e0", relief="solid", borderwidth=1)
        etapa_frame.pack(fill="x", pady=(0, 10), padx=0)
        
        etapa_label = Label(
            etapa_frame,
            text="📌 Selecione a Etapa",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#fff3e0",
            fg="#e65100"
        )
        etapa_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        etapa_radio_frame = Frame(etapa_frame, bg="#fff3e0")
        etapa_radio_frame.pack(fill="x", padx=10, pady=5)
        
        rb1 = Radiobutton(
            etapa_radio_frame,
            text="Etapa 1: Exportar pedidos (PDF → Modelo)",
            variable=self.etapa_selecionada,
            value="etapa1",
            bg="#fff3e0",
            fg="#333333",
            font=info_font
        )
        rb1.pack(anchor="w")
        
        rb2 = Radiobutton(
            etapa_radio_frame,
            text="Etapa 2: Extrair dados Excel (Pedidos → Modelo)",
            variable=self.etapa_selecionada,
            value="etapa2",
            bg="#fff3e0",
            fg="#333333",
            font=info_font
        )
        rb2.pack(anchor="w")
        
        # Configuração de max_orders
        config_frame = Frame(main_frame, bg="#e8f5e9", relief="solid", borderwidth=1)
        config_frame.pack(fill="x", pady=(0, 10), padx=0)
        
        config_label = Label(
            config_frame,
            text="⚙️  Configuração (Etapa 1 apenas)",
            font=tkFont.Font(family="Arial", size=9, weight="bold"),
            bg="#e8f5e9",
            fg="#1b5e20"
        )
        config_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        max_orders_frame = Frame(config_frame, bg="#e8f5e9")
        max_orders_frame.pack(fill="x", padx=10, pady=5)
        
        max_orders_label = Label(
            max_orders_frame,
            text="Quantos pedidos processar? *",
            font=info_font,
            bg="#e8f5e9",
            fg="#1b5e20"
        )
        max_orders_label.pack(side="left", padx=(0, 10))
        
        self.max_orders_entry = Entry(
            max_orders_frame,
            textvariable=self.max_orders,
            font=info_font,
            width=8,
            justify="center"
        )
        self.max_orders_entry.pack(side="left")
        
        # Dica
        dica = Label(
            max_orders_frame,
            text="(ex: 5, 10, 100)",
            font=tkFont.Font(family="Arial", size=8),
            bg="#e8f5e9",
            fg="#666666"
        )
        dica.pack(side="left", padx=(5, 0))
        
        # Área de logs
        log_label = Label(
            main_frame,
            text="📋 Saída da automação:",
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#f0f0f0",
            fg="#333333"
        )
        log_label.pack(anchor="w", pady=(5, 0))
        
        # Text com scrollbar
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
            height=12
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Botões
        button_frame = Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")
        
        self.button_etapa1 = Button(
            button_frame,
            text="▶️  INICIAR ETAPA 1",
            command=lambda: self.start_automation_etapa("etapa1"),
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#2196F3",
            fg="white",
            padx=15,
            pady=8,
            relief="raised",
            borderwidth=2
        )
        self.button_etapa1.pack(side="left", expand=True, padx=5)
        
        self.button_etapa2 = Button(
            button_frame,
            text="▶️  INICIAR ETAPA 2",
            command=lambda: self.start_automation_etapa("etapa2"),
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#FF9800",
            fg="white",
            padx=15,
            pady=8,
            relief="raised",
            borderwidth=2
        )
        self.button_etapa2.pack(side="left", expand=True, padx=5)
        
        close_button = Button(
            button_frame,
            text="❌ FECHAR",
            command=self.close_app,
            font=tkFont.Font(family="Arial", size=10, weight="bold"),
            bg="#f44336",
            fg="white",
            padx=15,
            pady=8,
            relief="raised",
            borderwidth=2
        )
        close_button.pack(side="right", expand=True, padx=5)
        
        # Registra hotkeys
        keyboard.add_hotkey("f6", lambda: self.start_automation_etapa("etapa1"))
        keyboard.add_hotkey("f7", lambda: self.start_automation_etapa("etapa2"))
        keyboard.add_hotkey("esc", self.close_app)
        
        self.log("✅ Hotkey Launcher iniciado")
        self.log("   F6: Iniciar Etapa 1 (PDF export)")
        self.log("   F7: Iniciar Etapa 2 (Excel extraction)")
        self.log("   ESC: Fechar aplicação")
    
    def log(self, message):
        """Adiciona mensagem ao log"""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update()
        print(message)  # Também imprime no console
    
    def toggle_automation(self):
        """Inicia ou para a automação (DEPRECATED - use start_automation_etapa)"""
        if not self.is_running:
            self.start_automation_etapa(self.etapa_selecionada.get())
        else:
            self.stop_automation()
    
    def start_automation_etapa(self, etapa: str):
        """Inicia automação de uma etapa específica"""
        if etapa == "etapa1":
            self.start_automation_etapa1()
        elif etapa == "etapa2":
            self.start_automation_etapa2()
        else:
            self.log(f"❌ Etapa desconhecida: {etapa}")
    
    def start_automation_etapa1(self):
        """Inicia a automação Etapa 1 (PDF export)"""
        if self.is_running:
            self.log("⚠️  Automação já em execução")
            return
        
        # Valida o campo de max_orders
        try:
            max_orders_val = int(self.max_orders.get())
            if max_orders_val <= 0:
                self.log("❌ Erro: Digite um número maior que 0 (ex: 5, 10, 100)")
                return
        except ValueError:
            self.log("❌ Erro: Digite um número válido (ex: 5, 10, 100)")
            return
        
        # Obtém o diretório de saída
        output_dir = Path(__file__).parent / "out"
        output_dir.mkdir(exist_ok=True)
        
        # Atualiza UI
        self.is_running = True
        self.status_label.config(
            text="🟢 EXECUTANDO ETAPA 1",
            bg="#ccffcc",
            fg="#009900"
        )
        self.button_etapa1.config(text="⏹️  PARAR", bg="#ff9800")
        self.button_etapa2.config(state="disabled")
        self.max_orders_entry.config(state="disabled")
        self.root.update()
        
        # Inicia automação em thread
        thread = threading.Thread(
            target=self._run_automation_etapa1,
            args=(str(output_dir),),
            daemon=True
        )
        thread.start()
        self.log(f"▶️  Iniciando ETAPA 1 (PDF export)...")
        self.log(f"   Diretório de saída: {output_dir}")
    
    def start_automation_etapa2(self):
        """Inicia a automação Etapa 2 (Excel extraction)"""
        if self.is_running:
            self.log("⚠️  Automação já em execução")
            return
        
        # Atualiza UI
        self.is_running = True
        self.status_label.config(
            text="🟡 EXECUTANDO ETAPA 2",
            bg="#ffffcc",
            fg="#ff8800"
        )
        self.button_etapa2.config(text="⏹️  PARAR", bg="#4CAF50")
        self.button_etapa1.config(state="disabled")
        self.max_orders_entry.config(state="disabled")
        self.root.update()
        
        # Inicia automação em thread
        thread = threading.Thread(
            target=self._run_automation_etapa2,
            daemon=True
        )
        thread.start()
        self.log(f"▶️  Iniciando ETAPA 2 (Excel extraction)...")
    
    def _run_automation_etapa1(self, output_dir):
        """Executa a automação Etapa 1 (rodando em thread)"""
        try:
            python_exe = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
            
            if not python_exe.exists():
                self.log(f"❌ Python não encontrado em: {python_exe}")
                self.show_error("Python virtual env não encontrado")
                return
            
            cmd = [
                str(python_exe),
                "-m", "src.main",
                "--output-dir", output_dir
            ]
            
            # Adiciona max_orders
            try:
                max_orders_val = int(self.max_orders.get())
                if max_orders_val > 0:
                    cmd.extend(["--max-orders", str(max_orders_val)])
                    self.log(f"⚙️  Máximo de pedidos: {max_orders_val}")
                else:
                    self.log(f"⚙️  Erro: Max orders deve ser > 0")
                    return
            except ValueError:
                self.log("⚙️  Erro: Max orders inválido")
                return
            
            self.log(f"▶️  Executando: {' '.join(cmd)}")
            
            # Usa Popen para que seja não-bloqueante
            self.process = subprocess.Popen(
                cmd,
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.log(f"✅ Processo iniciado (PID: {self.process.pid})")
            
            # Lê a saída em tempo real
            while True:
                if self.process.poll() is not None:
                    # Processo terminou
                    break
                
                line = self.process.stdout.readline()
                if line:
                    self.log(f"   {line.rstrip()}")
            
            # Lê resíduos
            remaining_stdout, remaining_stderr = self.process.communicate()
            if remaining_stdout:
                for line in remaining_stdout.split('\n'):
                    if line.strip():
                        self.log(f"   {line}")
            
            if self.process.returncode == 0:
                self.log("✅ Etapa 1 concluída com sucesso!")
            else:
                self.log(f"❌ Etapa 1 finalizou com código: {self.process.returncode}")
                if remaining_stderr:
                    self.log(f"Erro:\n{remaining_stderr}")
        
        except Exception as e:
            self.log(f"❌ Erro ao executar Etapa 1: {e}")
            self.show_error(f"Erro: {str(e)}")
        
        finally:
            # Reseta UI
            self.is_running = False
            self.process = None
            self.status_label.config(
                text="⏹️  PARADA",
                bg="#ffcccc",
                fg="#990000"
            )
            self.button_etapa1.config(text="▶️  INICIAR ETAPA 1", bg="#2196F3", state="normal")
            self.button_etapa2.config(state="normal")
            self.max_orders_entry.config(state="normal")
            self.root.update()
            self.log("="*50)
    
    def _run_automation_etapa2(self):
        """Executa a automação Etapa 2 (rodando em thread)"""
        try:
            python_exe = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
            
            if not python_exe.exists():
                self.log(f"❌ Python não encontrado em: {python_exe}")
                self.show_error("Python virtual env não encontrado")
                return
            
            cmd = [
                str(python_exe),
                "main_etapa2.py"
            ]
            
            self.log(f"▶️  Executando: {' '.join(cmd)}")
            
            # Usa Popen para que seja não-bloqueante
            self.process = subprocess.Popen(
                cmd,
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.log(f"✅ Processo iniciado (PID: {self.process.pid})")
            
            # Lê a saída em tempo real
            while True:
                if self.process.poll() is not None:
                    # Processo terminou
                    break
                
                line = self.process.stdout.readline()
                if line:
                    self.log(f"   {line.rstrip()}")
            
            # Lê resíduos
            remaining_stdout, remaining_stderr = self.process.communicate()
            if remaining_stdout:
                for line in remaining_stdout.split('\n'):
                    if line.strip():
                        self.log(f"   {line}")
            
            if self.process.returncode == 0:
                self.log("✅ Etapa 2 concluída com sucesso!")
            else:
                self.log(f"❌ Etapa 2 finalizou com código: {self.process.returncode}")
                if remaining_stderr:
                    self.log(f"Erro:\n{remaining_stderr}")
        
        except Exception as e:
            self.log(f"❌ Erro ao executar Etapa 2: {e}")
            self.show_error(f"Erro: {str(e)}")
        
        finally:
            # Reseta UI
            self.is_running = False
            self.process = None
            self.status_label.config(
                text="⏹️  PARADA",
                bg="#ffcccc",
                fg="#990000"
            )
            self.button_etapa2.config(text="▶️  INICIAR ETAPA 2", bg="#FF9800", state="normal")
            self.button_etapa1.config(state="normal")
            self.max_orders_entry.config(state="normal")
            self.root.update()
            self.log("="*50)
    
    def stop_automation(self):
        """Para a automação em execução"""
        if not self.process:
            self.log("⚠️  Nenhum processo em execução")
            return
        
        try:
            self.log(f"\n⏹️  Parando processo (PID: {self.process.pid})...")
            # Tenta terminar graciosamente primeiro
            self.process.terminate()
            
            try:
                self.process.wait(timeout=3)
                self.log("✅ Automação parada")
            except subprocess.TimeoutExpired:
                # Se não terminar em 3s, mata forçadamente
                self.log("⚠️  Forçando encerramento...")
                self.process.kill()
                self.process.wait()
                self.log("⚠️  Automação forçadamente encerrada")
        
        except Exception as e:
            self.log(f"❌ Erro ao parar: {e}")
        
        finally:
            self.is_running = False
            self.process = None
            self.status_label.config(
                text="⏹️  PARADA",
                bg="#ffcccc",
                fg="#990000"
            )
            self.toggle_button.config(text="▶️  INICIAR", bg="#4CAF50")
            self.max_orders_entry.config(state="normal")
            self.root.update()
            self.log("="*50)
    
    def show_error(self, message):
        """Mostra erro e reseta UI"""
        self.log(f"❌ {message}")
        self.is_running = False
        self.status_label.config(text=f"❌ ERRO", bg="#ffcccc", fg="#990000")
        self.toggle_button.config(text="▶️  INICIAR", bg="#4CAF50")
        self.max_orders_entry.config(state="normal")
        self.root.update()
    
    def close_app(self):
        """Fecha a aplicação"""
        if self.is_running:
            self.log("⚠️  Parando automação antes de fechar...")
            self.stop_automation()
        
        self.log("\n👋 Encerrando Hotkey Launcher...")
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Inicia a aplicação"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close_app()
        except Exception as e:
            self.log(f"❌ Erro fatal: {e}")
            import traceback
            self.log(traceback.format_exc())


if __name__ == "__main__":
    # Verifica Tesseract antes de iniciar
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    
    tesseract_found = any(Path(p).exists() for p in tesseract_paths)
    
    if not tesseract_found:
        import subprocess
        from tkinter import messagebox
        
        root_temp = Tk()
        root_temp.withdraw()
        
        result = messagebox.showinfo(
            "Tesseract OCR nao encontrado",
            "Tesseract OCR e necessario para extrair nomes de clientes automaticamente.\n\n"
            "Para instalar:\n"
            "1. Visite: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Clique em 'Downloads' (lado esquerdo)\n"
            "3. Baixe: tesseract-ocr-w64-setup-v*.exe\n"
            "4. Execute e instale em: C:\\Program Files\\Tesseract-OCR\n"
            "5. Reinicie a automacao\n\n"
            "Enquanto isso, voc pode digitar manualmente os nomes dos clientes.\n\n"
            "Clique OK para continuar..."
        )
        
        root_temp.destroy()
    
    launcher = HotKeyLauncher()
    launcher.run()
