#!/usr/bin/env python3
"""
Hotkey Launcher para Automação Mercos
Tecla F6: iniciar/parar automação
Tecla ESC: fechar a aplicação
"""

import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import Tk, Label, Button, Frame, Text, Scrollbar, Entry, StringVar
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
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Agora cria StringVar DEPOIS de ter a janela raiz
        self.max_orders = StringVar(value="0")  # 0 = processar todos
        
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
            text="🟢 F6: Iniciar/Parar  |  🔴 ESC: Fechar",
            font=info_font,
            bg="#f0f0f0",
            fg="#333333"
        )
        info1.pack(anchor="w")
        
        # Configuração de max_orders
        config_frame = Frame(main_frame, bg="#e8f5e9", relief="solid", borderwidth=1)
        config_frame.pack(fill="x", pady=(0, 10), padx=0)
        
        config_label = Label(
            config_frame,
            text="⚙️  Configuração",
            font=tkFont.Font(family="Arial", size=9, weight="bold"),
            bg="#e8f5e9",
            fg="#1b5e20"
        )
        config_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        max_orders_frame = Frame(config_frame, bg="#e8f5e9")
        max_orders_frame.pack(fill="x", padx=10, pady=5)
        
        max_orders_label = Label(
            max_orders_frame,
            text="Máximo de pedidos (0=todos):",
            font=info_font,
            bg="#e8f5e9",
            fg="#333333"
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
        
        self.toggle_button = Button(
            button_frame,
            text="▶️  INICIAR",
            command=self.toggle_automation,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=8,
            relief="raised",
            borderwidth=2
        )
        self.toggle_button.pack(side="left", expand=True, padx=5)
        
        close_button = Button(
            button_frame,
            text="❌ FECHAR",
            command=self.close_app,
            font=tkFont.Font(family="Arial", size=11, weight="bold"),
            bg="#f44336",
            fg="white",
            padx=20,
            pady=8,
            relief="raised",
            borderwidth=2
        )
        close_button.pack(side="right", expand=True, padx=5)
        
        # Registra hotkeys
        keyboard.add_hotkey("f6", self.toggle_automation)
        keyboard.add_hotkey("esc", self.close_app)
        
        self.log("✅ Hotkey Launcher iniciado")
        self.log("   F6: Iniciar/Parar automação")
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
        """Inicia ou para a automação"""
        if not self.is_running:
            self.start_automation()
        else:
            self.stop_automation()
    
    def start_automation(self):
        """Inicia a automação em thread separada"""
        if self.is_running:
            self.log("⚠️  Automação já em execução")
            return
        
        # Obtém o diretório de saída
        output_dir = Path(__file__).parent / "out"
        output_dir.mkdir(exist_ok=True)
        
        # Atualiza UI
        self.is_running = True
        self.status_label.config(
            text="🟢 EXECUTANDO",
            bg="#ccffcc",
            fg="#009900"
        )
        self.toggle_button.config(text="⏹️  PARAR", bg="#ff9800")
        self.max_orders_entry.config(state="disabled")
        self.root.update()
        
        # Inicia automação em thread
        thread = threading.Thread(
            target=self._run_automation,
            args=(str(output_dir),),
            daemon=True
        )
        thread.start()
        self.log(f"▶️  Iniciando thread de automação...")
        self.log(f"   Diretório de saída: {output_dir}")
    
    def _run_automation(self, output_dir):
        """Executa a automação (rodando em thread)"""
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
            
            # Adiciona max_orders se especificado
            try:
                max_orders_val = int(self.max_orders.get())
                if max_orders_val > 0:
                    cmd.extend(["--max-orders", str(max_orders_val)])
                    self.log(f"⚙️  Máximo de pedidos: {max_orders_val}")
                else:
                    self.log(f"⚙️  Processando todos os pedidos visíveis")
            except ValueError:
                self.log("⚠️  max_orders inválido, usando 0 (processar todos)")
            
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
                self.log("✅ Automação concluída com sucesso!")
            else:
                self.log(f"❌ Automação finalizou com código: {self.process.returncode}")
                if remaining_stderr:
                    self.log(f"Erro:\n{remaining_stderr}")
        
        except Exception as e:
            self.log(f"❌ Erro ao executar automação: {e}")
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
            self.toggle_button.config(text="▶️  INICIAR", bg="#4CAF50")
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
            "1. Visite: https://github.com/UB-Mannheim/tesseract/releases\n"
            "2. Baixe: tesseract-ocr-w64-setup-v*.exe\n"
            "3. Execute e instale em: C:\\Program Files\\Tesseract-OCR\n"
            "4. Reinicie a automacao\n\n"
            "Enquanto isso, voc pode digitar manualmente os nomes dos clientes.\n\n"
            "Clique OK para continuar..."
        )
        
        root_temp.destroy()
    
    launcher = HotKeyLauncher()
    launcher.run()
