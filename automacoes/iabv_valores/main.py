#!/usr/bin/env python
"""
IABV Valores — Atualização automática da planilha de valores por cliente.

Lê PDFs de pedidos IABV, extrai cliente + "Total da AC.", faz matching
contra a planilha Excel e soma os valores na coluna do ano configurado.

Uso:
    python main.py

Configuração: iabv_valores_config.json (mesmo diretório deste script)
"""

from __future__ import annotations

import json
import logging
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).parent))

from src.excel_updater import Config, executar

CONFIG_PATH = Path(__file__).parent / "iabv_valores_config.json"
LOG_PATH = Path(__file__).parent / "out" / "iabv_valores.log"

# Configurações fixas por ano
_ANO_CONFIG = {
    "2026": {
        "pdfs_dir": r"C:\Users\enzop\OneDrive\Área de Trabalho\PDF Valores Clientes\2026",
        "coluna_ano": "2026",
    },
    "2025": {
        "pdfs_dir": r"C:\Users\enzop\OneDrive\Área de Trabalho\PDF Valores Clientes\2025",
        "coluna_ano": "2025",
    },
}


def _selecionar_ano() -> str | None:
    """Abre um diálogo para o usuário escolher o ano. Retorna '2025', '2026' ou None se cancelar."""
    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("IABV Valores — Selecionar Ano")
    dialog.resizable(False, False)
    dialog.grab_set()

    # Centraliza na tela
    dialog.update_idletasks()
    w, h = 320, 160
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    dialog.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    tk.Label(
        dialog,
        text="Qual ano deseja processar?",
        font=("Segoe UI", 11),
        pady=16,
    ).pack()

    ano_escolhido: list[str | None] = [None]

    def escolher(ano: str) -> None:
        ano_escolhido[0] = ano
        dialog.destroy()

    frame_botoes = tk.Frame(dialog)
    frame_botoes.pack(pady=8)

    tk.Button(
        frame_botoes,
        text="  2026  ",
        font=("Segoe UI", 12, "bold"),
        bg="#1976D2",
        fg="white",
        activebackground="#1565C0",
        activeforeground="white",
        relief="flat",
        padx=16,
        pady=6,
        cursor="hand2",
        command=lambda: escolher("2026"),
    ).pack(side="left", padx=12)

    tk.Button(
        frame_botoes,
        text="  2025  ",
        font=("Segoe UI", 12),
        bg="#546E7A",
        fg="white",
        activebackground="#455A64",
        activeforeground="white",
        relief="flat",
        padx=16,
        pady=6,
        cursor="hand2",
        command=lambda: escolher("2025"),
    ).pack(side="left", padx=12)

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    root.wait_window(dialog)
    root.destroy()

    return ano_escolhido[0]


def _configurar_logging() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-8s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_PATH, encoding="utf-8", mode="w"),
        ],
    )


def _carregar_config(ano: str) -> Config:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {CONFIG_PATH}\n"
            f"Copie 'config.example.json' para '{CONFIG_PATH.name}' e preencha os campos."
        )

    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    campos_obrigatorios = ["excel_path"]
    faltando = [c for c in campos_obrigatorios if c not in raw]
    if faltando:
        raise ValueError(f"Campos obrigatórios faltando no config: {faltando}")

    # Sobrescreve pdfs_dir e coluna_ano com base no ano selecionado
    ano_cfg = _ANO_CONFIG[ano]

    return Config(
        pdfs_dir=Path(ano_cfg["pdfs_dir"]),
        excel_path=Path(raw["excel_path"]),
        coluna_ano=ano_cfg["coluna_ano"],
        limiar_fuzzy=float(raw.get("limiar_fuzzy", 0.75)),
        dry_run=bool(raw.get("dry_run", False)),
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Seleciona o ano antes de tudo
    ano = _selecionar_ano()
    if ano is None:
        print("Operação cancelada pelo usuário.")
        return 0

    _configurar_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info(f"IABV Valores — Iniciando (ano: {ano})")
    logger.info("=" * 60)

    try:
        config = _carregar_config(ano)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Erro na configuração: {e}")
        return 1

    if not config.pdfs_dir.exists():
        logger.error(f"Pasta de PDFs não encontrada: {config.pdfs_dir}")
        return 1

    if not config.excel_path.exists():
        logger.error(f"Planilha não encontrada: {config.excel_path}")
        return 1

    if config.dry_run:
        logger.info("*** MODO DRY RUN — Excel não será alterado ***")

    logger.info(f"PDFs:    {config.pdfs_dir}")
    logger.info(f"Excel:   {config.excel_path}")
    logger.info(f"Ano:     {config.coluna_ano}")
    logger.info("-" * 60)

    try:
        resumo = executar(config)
    except Exception as e:
        logger.error(f"Erro durante execução: {e}", exc_info=True)
        return 1

    # --- Relatório final ---
    logger.info("=" * 60)
    logger.info("RESUMO")
    logger.info(f"  PDFs processados:      {resumo.total_pdfs - resumo.pdfs_com_erro}/{resumo.total_pdfs}")
    logger.info(f"  Clientes atualizados:  {resumo.clientes_atualizados}")
    logger.info(f"  Matches exatos:        {resumo.matches_exatos}")
    logger.info(f"  Matches por alias:     {resumo.matches_alias}")
    logger.info(f"  Matches por substring: {resumo.matches_substring}")
    logger.info(f"  Matches fuzzy (!):     {resumo.matches_fuzzy}")
    logger.info(f"  Nao identificados (X): {len(resumo.nao_identificados)}")

    if resumo.nao_identificados:
        nao_id_path = LOG_PATH.parent / "nao_identificados.txt"
        nao_id_path.write_text(
            "\n".join(resumo.nao_identificados), encoding="utf-8"
        )
        logger.warning(f"  Lista salva em: {nao_id_path}")
        logger.warning("  Verifique e adicione aliases na coluna G da planilha.")

    if resumo.matches_fuzzy > 0:
        logger.warning("  (!) Verifique os matches fuzzy no log - podem ser incorretos.")

    logger.info("=" * 60)

    if config.dry_run:
        logger.info("DRY RUN concluído. Nenhuma alteração foi feita.")
    else:
        logger.info("Planilha atualizada com sucesso.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
