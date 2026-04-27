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
        time.sleep(2.0)  # Delay apos F10
        for _ in range(self.config.report_variation_down_presses):
            self._press("down")
            time.sleep(0.5)  # Delay entre setas
        time.sleep(1.0)  # Delay apos ultima seta
        self._press(self.config.report_variation_confirm_key)
        time.sleep(2.0)  # Delay apos ESC
        # Verificar se popup apareceu apos confirmar selecao
        self._press(self.config.optional_popup_key)
        time.sleep(3.0)  # Delay apos ENTER (antes do PDF)

    def export_to_pdf(self) -> None:
        if self.config.export_pdf_button is None:
            raise RuntimeError("export_pdf_button is not configured")

        pyautogui.click(self.config.export_pdf_button.x, self.config.export_pdf_button.y)
        time.sleep(2.0)  # Delay apos clique no PDF
        self._press("enter")
        time.sleep(2.0)  # Delay apos ENTER de confirmacao

    def save_pdf(self, customer_name: str) -> Path:
        safe_name = self._safe_filename(customer_name)
        file_path = self.output_dir / f"{safe_name}.pdf"

        if self.config.save_dialog_filename_field is not None:
            pyautogui.click(
                self.config.save_dialog_filename_field.x,
                self.config.save_dialog_filename_field.y,
            )
            time.sleep(self.config.ui_delay)
            
            # Double-click para selecionar todo o texto
            pyautogui.click(
                self.config.save_dialog_filename_field.x,
                self.config.save_dialog_filename_field.y,
            )
            time.sleep(0.1)

        # Seleciona tudo (Ctrl+A)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(self.config.ui_delay * 2)
        
        # Escreve o novo nome
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
            LOGGER.warning("customer_name_region not configured; asking user for name")
            return self._ask_user_for_name()

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
                extracted = self._sanitize_customer_name(result.text)
                LOGGER.info(f"OCR extracted: {extracted}")
                return extracted
        except Exception as exc:  # pragma: no cover - runtime fallback
            LOGGER.warning("OCR failed: %s", exc)

        LOGGER.warning("OCR extraction failed; asking user for name")
        return self._ask_user_for_name()

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

    def _ask_user_for_name(self) -> str:
        """Abre um popup para o usuário digitar o nome do cliente"""
        try:
            from tkinter import Tk, simpledialog
            
            root = Tk()
            root.withdraw()  # Esconde a janela principal
            root.attributes("-topmost", True)  # Coloca o popup no topo
            
            name = simpledialog.askstring(
                "Nome do Cliente",
                f"Digite o nome do cliente (Pedido #{self._processed + 1}):",
                parent=root
            )
            
            root.destroy()
            
            if name:
                return self._sanitize_customer_name(name)
        except Exception as exc:
            LOGGER.error(f"Failed to ask user for name: {exc}")
        
        # Se algo falhar ou usuário cancelar, usa fallback
        return self._fallback_name()

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
