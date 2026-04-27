@echo off
chcp 65001 > nul
REM Hotkey Launcher - F6 para iniciar/parar automação
cd /d "%~dp0"
.\.venv\Scripts\python.exe hotkey_launcher.py
pause
