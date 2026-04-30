from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import logging
import sys

from .automation import MercosAutomation, load_automation_config


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Automacao de exportacao de pedidos Mercos para PDF")
    parser.add_argument("--output-dir", required=True, help="Pasta de saida dos PDFs")
    _default_config = str(Path(__file__).parent.parent / "automation_config.json")
    parser.add_argument("--config", default=_default_config, help="Arquivo JSON de configuracao")
    parser.add_argument("--max-orders", type=int, default=None, help="Limite opcional de pedidos nesta execucao")
    parser.add_argument("--log-level", default="INFO", help="Nivel de log")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    
    # Força UTF-8 no console Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # Configura logging com console E arquivo
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "automation.log"
    
    # Cria formatter
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s: %(message)s")
    
    # Configura root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, args.log_level.upper(), logging.INFO))
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para arquivo
    try:
        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        print(f"Logs salvos em: {log_file}")
    except Exception as e:
        print(f"Erro ao criar arquivo de log: {e}")

    config_path = Path(args.config)
    config = load_automation_config(config_path)
    if args.max_orders is not None:
        config.max_orders = args.max_orders

    output_dir = Path(args.output_dir)
    automation = MercosAutomation(config=config, output_dir=output_dir)
    automation.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
