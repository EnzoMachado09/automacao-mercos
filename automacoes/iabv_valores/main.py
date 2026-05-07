#!/usr/bin/env python
"""
IABV Valores — Atualização automática da planilha de valores por cliente.

Lê PDFs de pedidos IABV, extrai cliente + "Total da AC.", faz matching
contra a planilha Excel e soma os valores na coluna do ano configurado.

Uso:
    python main.py --ano 2026
    python main.py --ano 2025

Configuração: iabv_valores_config.json (mesmo diretório deste script)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.excel_updater import Config, executar
from src.name_matcher import normalizar

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

    if "excel_path" not in raw:
        raise ValueError("Campo obrigatório 'excel_path' faltando no config.")

    ano_cfg = _ANO_CONFIG[ano]

    blacklist_raw: list[str] = raw.get("fuzzy_blacklist", [])
    fuzzy_blacklist = {normalizar(nome) for nome in blacklist_raw}

    return Config(
        pdfs_dir=Path(ano_cfg["pdfs_dir"]),
        excel_path=Path(raw["excel_path"]),
        coluna_ano=ano_cfg["coluna_ano"],
        limiar_fuzzy=float(raw.get("limiar_fuzzy", 0.75)),
        dry_run=bool(raw.get("dry_run", False)),
        fuzzy_blacklist=fuzzy_blacklist,
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--ano", choices=["2025", "2026"], required=True,
                        help="Ano a processar (2025 ou 2026)")
    args = parser.parse_args()
    ano = args.ano

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
    if config.fuzzy_blacklist:
        logger.info(f"Blacklist fuzzy: {len(config.fuzzy_blacklist)} cliente(s) bloqueado(s)")
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
