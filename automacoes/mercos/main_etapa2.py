#!/usr/bin/env python
"""
Script de execução da Etapa 2 - Anotar Informações dos Pedidos

Uso:
    python main_etapa2.py

Requisitos:
    - openpyxl instalado
    - Arquivo de configuração: etapa2_config.json
"""

import sys
import json
import logging
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from excel_automation import ExcelAutomation, ExcelPaths

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("out/etapa2_automation.log", encoding="utf-8")
    ]
)

LOGGER = logging.getLogger(__name__)


def main():
    """Executa automação da Etapa 2"""
    
    # Carregar configuração
    config_path = Path(__file__).parent / "etapa2_config.json"
    
    if not config_path.exists():
        LOGGER.error(f"❌ Arquivo de configuração não encontrado: {config_path}")
        return 1
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        LOGGER.error(f"❌ Erro ao ler configuração: {e}")
        return 1
    
    # Validar configuração
    if "modelo_path" not in config or "pedidos_input_dir" not in config or "output_dir" not in config:
        LOGGER.error("❌ Configuração incompleta. Necessários: modelo_path, pedidos_input_dir, output_dir")
        return 1

    # Resolve modelo_path: aceita arquivo .xlsx ou pasta contendo 1+ .xlsx
    modelo_path = Path(config["modelo_path"])
    if modelo_path.is_dir():
        candidatos = sorted(modelo_path.glob("*.xlsx"))
        if not candidatos:
            LOGGER.error(f"❌ Nenhum .xlsx encontrado na pasta de modelo: {modelo_path}")
            return 1
        if len(candidatos) > 1:
            LOGGER.warning(f"⚠️ Mais de um modelo encontrado. Usando: {candidatos[0].name}")
        modelo_path = candidatos[0]
    
    # Criar objetos Path
    try:
        paths = ExcelPaths(
            modelo_path=modelo_path,
            pedidos_input_dir=Path(config["pedidos_input_dir"]),
            output_dir=Path(config["output_dir"]),
        )
    except (FileNotFoundError, NotADirectoryError) as e:
        LOGGER.error(f"❌ {e}")
        return 1
    
    # Executar automação
    try:
        automacao = ExcelAutomation(paths)
        automacao.run()
        LOGGER.info("✅ Automação concluída com sucesso!")
        return 0
    
    except Exception as e:
        LOGGER.error(f"❌ Erro durante execução: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
