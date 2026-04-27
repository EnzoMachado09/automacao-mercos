from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import logging

from .automation import MercosAutomation, load_automation_config
from .config import default_config_path


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Automacao de exportacao de pedidos Mercos para PDF")
    parser.add_argument("--start-date", required=True, help="Data inicial do periodo")
    parser.add_argument("--end-date", required=True, help="Data final do periodo")
    parser.add_argument("--output-dir", required=True, help="Pasta de saida dos PDFs")
    parser.add_argument("--config", default=str(default_config_path()), help="Arquivo JSON de configuracao")
    parser.add_argument("--max-orders", type=int, default=None, help="Limite opcional de pedidos nesta execucao")
    parser.add_argument("--log-level", default="INFO", help="Nivel de log")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config_path = Path(args.config)
    config = load_automation_config(config_path)
    if args.max_orders is not None:
        config.max_orders = args.max_orders

    output_dir = Path(args.output_dir)
    automation = MercosAutomation(config=config, output_dir=output_dir)
    automation.run(start_date=args.start_date, end_date=args.end_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
