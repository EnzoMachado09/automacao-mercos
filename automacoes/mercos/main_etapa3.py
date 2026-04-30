#!/usr/bin/env python
"""
Script de execução da Etapa 3 - Criar Pedidos no Mercos Web

Uso:
    python main_etapa3.py

Requisitos:
    - playwright instalado: .venv/Scripts/pip install playwright
    - Browser instalado:    .venv/Scripts/playwright install chromium
    - Arquivo de configuração: etapa3_config.json
    - Arquivos * M.xlsx e * M.json gerados pela Etapa 2
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mercos_web_automation import MercosWebAutomation, Etapa3Config

Path("out").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("out/etapa3_automation.log", encoding="utf-8"),
    ],
)

LOGGER = logging.getLogger(__name__)


def _verificar_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


def main() -> int:
    config_path = Path(__file__).parent / "etapa3_config.json"

    if not config_path.exists():
        LOGGER.error(f"❌ Configuração não encontrada: {config_path}")
        return 1

    try:
        dados = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        LOGGER.error(f"❌ Erro ao ler configuração: {e}")
        return 1

    obrigatorios = ["mercos_url", "representada", "output_dir"]
    faltando = [c for c in obrigatorios if not dados.get(c)]
    if faltando:
        LOGGER.error(f"❌ Campos obrigatórios ausentes em etapa3_config.json: {faltando}")
        return 1

    if not _verificar_playwright():
        LOGGER.error(
            "❌ Browser Playwright não instalado.\n"
            "   Execute: .venv\\Scripts\\playwright install chromium"
        )
        return 1

    config = Etapa3Config(
        mercos_url=dados["mercos_url"],
        email=dados.get("email", ""),
        senha=dados.get("senha", ""),
        representada=dados["representada"],
        condicao_pagamento=dados.get("condicao_pagamento", "a vista"),
        output_dir=Path(dados["output_dir"]),
        playwright_headless=dados.get("playwright_headless", False),
        playwright_slow_mo=dados.get("playwright_slow_mo", 500),
        timeout_elemento_ms=dados.get("timeout_elemento_ms", 10000),
    )

    try:
        automacao = MercosWebAutomation(config)
        automacao.run()
        LOGGER.info("✅ Etapa 3 concluída com sucesso!")
        return 0
    except Exception as e:
        LOGGER.error(f"❌ Erro durante execução: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
