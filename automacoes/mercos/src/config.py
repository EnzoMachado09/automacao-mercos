from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(slots=True)
class Point:
    x: int
    y: int


@dataclass(slots=True)
class Region:
    left: int
    top: int
    width: int
    height: int


@dataclass(slots=True)
class AutomationConfig:
    export_pdf_button: Point | None = None
    customer_name_region: Region | None = None
    selection_probe_region: Region | None = None
    save_dialog_filename_field: Point | None = None
    save_button: Point | None = None
    report_variation_down_presses: int = 6
    report_variation_confirm_key: str = "esc"
    optional_popup_key: str = "enter"
    advance_key: str = "down"
    advance_after_export_delay: float = 0.5
    ui_delay: float = 0.25
    export_confirm_delay: float = 0.7
    max_orders: int | None = None
    fallback_customer_name_prefix: str = "pedido"
    preserve_selection_after_export: bool = False
    extra_wait_on_popup: float = 0.3
    tesseract_cmd: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "AutomationConfig":
        if not path.exists():
            return cls()

        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AutomationConfig":
        def parse_point(value: Any) -> Point | None:
            if not value:
                return None
            return Point(x=int(value[0]), y=int(value[1]))

        def parse_region(value: Any) -> Region | None:
            if not value:
                return None
            return Region(
                left=int(value[0]),
                top=int(value[1]),
                width=int(value[2]),
                height=int(value[3]),
            )

        known_keys = {
            "export_pdf_button",
            "customer_name_region",
            "selection_probe_region",
            "save_dialog_filename_field",
            "save_button",
            "report_variation_down_presses",
            "report_variation_confirm_key",
            "optional_popup_key",
            "advance_key",
            "advance_after_export_delay",
            "ui_delay",
            "export_confirm_delay",
            "max_orders",
            "fallback_customer_name_prefix",
            "preserve_selection_after_export",
            "extra_wait_on_popup",
            "tesseract_cmd",
        }

        data = dict(raw)
        extra = {key: value for key, value in data.items() if key not in known_keys}

        return cls(
            export_pdf_button=parse_point(data.get("export_pdf_button")),
            customer_name_region=parse_region(data.get("customer_name_region")),
            selection_probe_region=parse_region(data.get("selection_probe_region")),
            save_dialog_filename_field=parse_point(data.get("save_dialog_filename_field")),
            save_button=parse_point(data.get("save_button")),
            report_variation_down_presses=int(data.get("report_variation_down_presses", 6)),
            report_variation_confirm_key=str(data.get("report_variation_confirm_key", "esc")),
            optional_popup_key=str(data.get("optional_popup_key", "enter")),
            advance_key=str(data.get("advance_key", "down")),
            advance_after_export_delay=float(data.get("advance_after_export_delay", 0.5)),
            ui_delay=float(data.get("ui_delay", 0.25)),
            export_confirm_delay=float(data.get("export_confirm_delay", 0.7)),
            max_orders=int(data["max_orders"]) if data.get("max_orders") is not None else None,
            fallback_customer_name_prefix=str(data.get("fallback_customer_name_prefix", "pedido")),
            preserve_selection_after_export=bool(data.get("preserve_selection_after_export", False)),
            extra_wait_on_popup=float(data.get("extra_wait_on_popup", 0.3)),
            tesseract_cmd=data.get("tesseract_cmd"),
            extra=extra,
        )


def default_config_path() -> Path:
    return Path.cwd() / "automation_config.json"
