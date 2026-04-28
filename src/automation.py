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
        self.cliente_contador: dict[str, int] = {}  # Rastreia quantas vezes cada cliente apareceu

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
        """Salva PDF com tratamento automático de duplicatas de clientes"""
        LOGGER.info(f"💾 Iniciando save_pdf para cliente: '{customer_name}'")
        
        # Obtém o nome base (sem números do final)
        base_name = self._get_base_name(customer_name)
        LOGGER.info(f"   Nome base extraído (ignorando números): '{base_name}'")
        
        # Obtém o nome que está no campo de save
        field_text = self._get_field_text()
        field_base = self._get_base_name(field_text) if field_text else ""
        LOGGER.info(f"   Nome no campo de save: '{field_text}' (base: '{field_base}')")
        
        # Determina o nome final com numeração automática
        if field_base and field_base == base_name:
            # Mesmo cliente (comparando sem números)
            LOGGER.info(f"⚠️  Cliente repetido detectado!")
            final_name = self._get_numbered_name(base_name)
        else:
            # Cliente novo
            final_name = self._get_numbered_name(base_name)
        
        safe_name = self._safe_filename(final_name)
        file_path = self.output_dir / f"{safe_name}.pdf"
        LOGGER.info(f"   Nome final para salvar: '{final_name}' → arquivo: '{file_path.name}'")

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
        LOGGER.info(f"✅ PDF salvo com sucesso: {file_path.name}")
        return file_path

    def read_customer_name(self) -> str:
        if self.config.customer_name_region is None:
            LOGGER.warning("customer_name_region not configured; asking user for name")
            return self._ask_user_for_name()

        LOGGER.info(f"📸 Capturando imagem da região de nome do cliente...")
        screenshot = pyautogui.screenshot(
            region=(
                self.config.customer_name_region.left,
                self.config.customer_name_region.top,
                self.config.customer_name_region.width,
                self.config.customer_name_region.height,
            )
        )

        try:
            # Salva screenshot de debug
            debug_path = self.output_dir / f"debug_ocr_{self._processed + 1:04d}.png"
            
            LOGGER.info(f"🔍 Iniciando OCR (Tesseract: {self.config.tesseract_cmd or 'padrão'})...")
            result = ocr_image(screenshot, tesseract_cmd=self.config.tesseract_cmd, debug_path=debug_path)
            
            LOGGER.info(f"📊 OCR Result - Confidence: {result.confidence:.1f}% | Text: '{result.text}'")
            LOGGER.info(f"📁 Debug image saved: {debug_path}")
            
            if result.text and result.confidence and result.confidence > 20:
                extracted = self._sanitize_customer_name(result.text)
                LOGGER.info(f"✅ OCR SUCCESS (confidence={result.confidence:.1f}%): '{extracted}'")
                return extracted
            else:
                confidence_val = result.confidence if result.confidence else 0
                LOGGER.warning(f"⚠️  OCR Confidence too low ({confidence_val:.1f}% < 20%)")
                LOGGER.warning(f"⚠️  OCR Text: '{result.text}'")
        
        except RuntimeError as e:
            # Timeout ou erro crítico do Tesseract
            if "timeout" in str(e).lower():
                LOGGER.error(f"❌ TESSERACT TIMEOUT: {e}")
                LOGGER.error("⚠️  Tesseract está demorando muito. Isso pode ser um problema de instalação.")
            else:
                LOGGER.error(f"❌ OCR Runtime Error: {e}", exc_info=True)
        except Exception as exc:  # pragma: no cover - runtime fallback
            LOGGER.error(f"❌ OCR Exception: {exc}", exc_info=True)

        LOGGER.warning("💬 OCR failed; asking user for name")
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

    def _get_base_name(self, name: str) -> str:
        """Remove números do final do nome para comparação (ex: 'ACESSOCAR 2' -> 'ACESSOCAR')"""
        import re
        # Remove ' 2', ' 3', etc do final
        base = re.sub(r'\s+\d+$', '', name)
        return base.strip()

    def _get_field_text(self) -> str:
        """Lê o texto atualmente no campo de save (via screenshot e OCR simples)"""
        if self.config.save_dialog_filename_field is None:
            return ""
        
        # Captura uma imagem pequena ao redor do campo
        region_size = 300  # largura aproximada
        x = self.config.save_dialog_filename_field.x
        y = self.config.save_dialog_filename_field.y
        
        try:
            screenshot = pyautogui.screenshot(
                region=(x - 50, y - 10, region_size, 30)
            )
            # Tenta extrair texto com OCR
            from .vision import ocr_image
            result = ocr_image(screenshot, tesseract_cmd=self.config.tesseract_cmd)
            text = normalize_text(result.text) if result.text else ""
            LOGGER.debug(f"Campo de save contém: '{text}'")
            return text
        except Exception as e:
            LOGGER.debug(f"Falha ao ler campo de save: {e}")
            return ""

    def _get_numbered_name(self, base_name: str) -> str:
        """Retorna o nome com numeração automática se for repetido"""
        if base_name not in self.cliente_contador:
            # Primeira vez que vê este cliente
            self.cliente_contador[base_name] = 1
            LOGGER.info(f"📊 Novo cliente: {base_name} (contagem: 1)")
            return base_name
        else:
            # Cliente já visto, incrementa contador
            self.cliente_contador[base_name] += 1
            count = self.cliente_contador[base_name]
            numbered_name = f"{base_name} {count}"
            LOGGER.info(f"📊 Cliente repetido: {base_name} (contagem: {count}) → salvando como '{numbered_name}'")
            return numbered_name


def load_automation_config(config_path: Path) -> AutomationConfig:
    return AutomationConfig.from_file(config_path)
