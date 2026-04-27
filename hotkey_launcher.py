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
from tkinter import Tk, Label, Button, Frame
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
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Tenta colocar a janela sempre no topo
        try:
            self.root.attributes("-topmost", True)
        except:
            pass
        
        # Define estilos
        title_font = tkFont.Font(family="Arial", size=14, weight="bold")
        status_font = tkFont.Font(family="Arial", size=12)
        info_font = tkFont.Font(family="Arial", size=10)
        
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
        title_label.pack(pady=(10, 20))
        
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
            pady=15
        )
        self.status_label.pack(fill="x", pady=(0, 15))
        
        # Instruções
        info_frame = Frame(main_frame, bg="#f0f0f0")
        info_frame.pack(fill="x", pady=(0, 15))
        
        info1 = Label(
            info_frame,
            text="🟢 F6: Iniciar/Parar",
            font=info_font,
            bg="#f0f0f0",
            fg="#333333"
        )
        info1.pack(anchor="w")
        
        info2 = Label(
            info_frame,
            text="🔴 ESC: Fechar",
            font=info_font,
            bg="#f0f0f0",
            fg="#333333"
        )
        info2.pack(anchor="w")
        
        # Botão manual
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
        
        print("✅ Hotkey Launcher iniciado")
        print("   F6: Iniciar/Parar automação")
        print("   ESC: Fechar aplicação")
    
    def toggle_automation(self):
        """Inicia ou para a automação"""
        if not self.is_running:
            self.start_automation()
        else:
            self.stop_automation()
    
    def start_automation(self):
        """Inicia a automação em thread separada"""
        if self.is_running:
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
        self.root.update()
        
        # Inicia automação em thread
        thread = threading.Thread(
            target=self._run_automation,
            args=(str(output_dir),),
            daemon=True
        )
        thread.start()
    
    def _run_automation(self, output_dir):
        """Executa a automação (rodando em thread)"""
        try:
            python_exe = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
            
            if not python_exe.exists():
                self.show_error("Python virtual env não encontrado")
                return
            
            cmd = [
                str(python_exe),
                "-m", "src.main",
                "--output-dir", output_dir
            ]
            
            print(f"\n▶️  Iniciando automação...")
            print(f"   Comando: {' '.join(cmd)}")
            
            # Usa Popen para que seja não-bloqueante
            self.process = subprocess.Popen(
                cmd,
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Aguarda o processo terminar
            stdout, stderr = self.process.communicate()
            
            if self.process.returncode == 0:
                print("✅ Automação concluída com sucesso!")
            else:
                print(f"❌ Automação finalizou com erro (código {self.process.returncode})")
                if stderr:
                    print(f"Erro:\n{stderr}")
                if stdout:
                    print(f"Saída:\n{stdout}")
        
        except Exception as e:
            print(f"❌ Erro ao executar automação: {e}")
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
            self.root.update()
    
    def stop_automation(self):
        """Para a automação em execução"""
        if not self.process:
            print("⚠️  Nenhum processo em execução")
            return
        
        try:
            print("\n⏹️  Parando automação...")
            # Tenta terminar graciosamente primeiro
            self.process.terminate()
            
            try:
                self.process.wait(timeout=3)
                print("✅ Automação parada")
            except subprocess.TimeoutExpired:
                # Se não terminar em 3s, mata forçadamente
                self.process.kill()
                self.process.wait()
                print("⚠️  Automação forçadamente encerrada")
        
        except Exception as e:
            print(f"❌ Erro ao parar: {e}")
        
        finally:
            self.is_running = False
            self.process = None
            self.status_label.config(
                text="⏹️  PARADA",
                bg="#ffcccc",
                fg="#990000"
            )
            self.toggle_button.config(text="▶️  INICIAR", bg="#4CAF50")
            self.root.update()
    
    def show_error(self, message):
        """Mostra erro e reseta UI"""
        print(f"❌ {message}")
        self.is_running = False
        self.status_label.config(text=f"❌ ERRO", bg="#ffcccc", fg="#990000")
        self.toggle_button.config(text="▶️  INICIAR", bg="#4CAF50")
        self.root.update()
    
    def close_app(self):
        """Fecha a aplicação"""
        if self.is_running:
            self.stop_automation()
        
        print("\n👋 Encerrando Hotkey Launcher...")
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Inicia a aplicação"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close_app()


if __name__ == "__main__":
    launcher = HotKeyLauncher()
    launcher.run()
