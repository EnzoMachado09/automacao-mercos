from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import time

import pyautogui

from .config import AutomationConfig, Region
from .vision import image_digest, normalize_text, ocr_image


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class OrderExportResult:
    order_index: int
    customer_name: str
    file_path: Path
    selection_moved: bool | None


class MercosAutomation:
    def __init__(self, config: AutomationConfig, output_dir: Path) -> None:
        self.config = config
        self.output_dir = output_dir
        self._processed = 0

    def run(self) -> list[OrderExportResult]:
        LOGGER.info("Starting automation for pedidos na lista")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.config.selection_probe_region is None and self.config.max_orders is None:
            raise RuntimeError("selection_probe_region or max_orders must be configured to stop the loop safely")

        results: list[OrderExportResult] = []
        while True:
            if self.config.max_orders is not None and self._processed >= self.config.max_orders:
                LOGGER.info("Reached max_orders=%s", self.config.max_orders)
                break

            self.open_report_variation()
            self.export_to_pdf()
            customer_name = self.read_customer_name()
            file_path = self.save_pdf(customer_name)
            selection_moved = self.advance_selection_if_possible()

            result = OrderExportResult(
                order_index=self._processed + 1,
                customer_name=customer_name,
                file_path=file_path,
                selection_moved=selection_moved,
            )
            results.append(result)
            self._processed += 1

            LOGGER.info(
                "Exported order %s as %s (selection moved=%s)",
                result.order_index,
                result.file_path.name,
                result.selection_moved,
            )

            if selection_moved is False:
                LOGGER.info("Selection no longer moved; finishing batch")
                break

            time.sleep(self.config.advance_after_export_delay)

        return results

    def export_current_order(self, customer_name: str) -> Path:
        self.export_to_pdf()
        file_path = self.save_pdf(customer_name)
        return file_path

    def open_report_variation(self) -> None:
        self._press("f10")
        self._sleep()
        for _ in range(self.config.report_variation_down_presses):
            self._press("down")
            self._sleep()
        self._press(self.config.report_variation_confirm_key)
        self._sleep()
        # Verificar se popup apareceu apos confirmar selecao
        self._press(self.config.optional_popup_key)
        time.sleep(self.config.extra_wait_on_popup)

    def export_to_pdf(self) -> None:
        if self.config.export_pdf_button is None:
            raise RuntimeError("export_pdf_button is not configured")

        pyautogui.click(self.config.export_pdf_button.x, self.config.export_pdf_button.y)
        time.sleep(self.config.export_confirm_delay)
        self._press("enter")
        time.sleep(self.config.export_confirm_delay)

    def save_pdf(self, customer_name: str) -> Path:
        safe_name = self._safe_filename(customer_name)
        file_path = self.output_dir / f"{safe_name}.pdf"

        if self.config.save_dialog_filename_field is not None:
            pyautogui.click(
                self.config.save_dialog_filename_field.x,
                self.config.save_dialog_filename_field.y,
            )
            time.sleep(self.config.ui_delay)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(self.config.ui_delay * 2)
        pyautogui.write(file_path.stem, interval=0.02)
        time.sleep(self.config.ui_delay * 2)
        
        if self.config.save_button is not None:
            pyautogui.click(self.config.save_button.x, self.config.save_button.y)
            time.sleep(self.config.export_confirm_delay)
        else:
            self._press("enter")
            time.sleep(self.config.ui_delay)
        
        self._press("esc")
        time.sleep(self.config.ui_delay)
        return file_path

    def read_customer_name(self) -> str:
        if self.config.customer_name_region is None:
            LOGGER.warning("customer_name_region not configured; using fallback name")
            return self._fallback_name()

        screenshot = pyautogui.screenshot(
            region=(
                self.config.customer_name_region.left,
                self.config.customer_name_region.top,
                self.config.customer_name_region.width,
                self.config.customer_name_region.height,
            )
        )

        try:
            result = ocr_image(screenshot, tesseract_cmd=self.config.tesseract_cmd)
            if result.text:
                return self._sanitize_customer_name(result.text)
        except Exception as exc:  # pragma: no cover - runtime fallback
            LOGGER.warning("OCR failed: %s", exc)

        return self._fallback_name()

    def advance_selection_if_possible(self) -> bool | None:
        if self.config.selection_probe_region is None:
            self._press(self.config.advance_key)
            self._sleep()
            return None

        before = self._capture_digest(self.config.selection_probe_region)
        self._press(self.config.advance_key)
        self._sleep()
        after = self._capture_digest(self.config.selection_probe_region)
        return before != after

    def _capture_digest(self, region: Region) -> str:
        screenshot = pyautogui.screenshot(region=(region.left, region.top, region.width, region.height))
        return image_digest(screenshot)

    def _fallback_name(self) -> str:
        return f"{self.config.fallback_customer_name_prefix}_{self._processed + 1:04d}"

    def _sanitize_customer_name(self, text: str) -> str:
        cleaned = normalize_text(text)
        cleaned = cleaned.replace("/", "-").replace("\\", "-")
        cleaned = cleaned.replace(":", "-").replace("*", "-")
        cleaned = cleaned.replace("?", "-").replace('"', "-")
        cleaned = cleaned.replace("<", "-").replace(">", "-").replace("|", "-")
        return cleaned.strip(" .") or self._fallback_name()

    def _safe_filename(self, value: str) -> str:
        cleaned = self._sanitize_customer_name(value)
        return cleaned[:180]

    def _press(self, key: str) -> None:
        pyautogui.press(key)

    def _sleep(self) -> None:
        time.sleep(self.config.ui_delay)


def load_automation_config(config_path: Path) -> AutomationConfig:
    return AutomationConfig.from_file(config_path)
