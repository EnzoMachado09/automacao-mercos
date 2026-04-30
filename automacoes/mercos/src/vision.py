from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import logging
import subprocess
import tempfile
import sys

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VisionResult:
    text: str
    confidence: float | None = None


def image_digest(image: Image.Image) -> str:
    return sha1(image.tobytes()).hexdigest()


def normalize_text(value: str) -> str:
    cleaned = " ".join(value.replace("\n", " ").replace("\r", " ").split())
    return cleaned.strip()


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocessa a imagem para melhorar OCR"""
    # Converte para RGB se necessário
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Aumenta contraste
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Aumenta brilho
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.2)
    
    # Aumenta nitidez
    image = image.filter(ImageFilter.SHARPEN)
    
    # Aumenta o tamanho para melhor OCR (upscaling)
    new_size = (image.width * 2, image.height * 2)
    image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    return image


def ocr_image(image: Image.Image, tesseract_cmd: str | None = None, debug_path: Path | None = None) -> VisionResult:
    if pytesseract is None:
        LOGGER.error("❌ pytesseract not installed!")
        raise RuntimeError("pytesseract is not installed")

    if tesseract_cmd:
        LOGGER.info(f"🔧 Setting Tesseract command: {tesseract_cmd}")
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        # Define TESSDATA_PREFIX automaticamente
        tesseract_dir = Path(tesseract_cmd).parent
        tessdata_dir = tesseract_dir / "tessdata"
        LOGGER.info(f"📚 Setting TESSDATA_PREFIX: {tessdata_dir}")
        import os
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
    else:
        LOGGER.info("🔧 Using default Tesseract from PATH")

    # Preprocessa a imagem
    LOGGER.info("🖼️  Preprocessing image (contrast, brightness, sharpness, upscale)")
    processed_image = _preprocess_image(image)
    
    # Salva screenshot de debug se solicitado
    if debug_path:
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        processed_image.save(debug_path)
        LOGGER.info(f"💾 Saved debug image: {debug_path}")
    
    # Tenta OCR em português com timeout
    # Tenta OCR com fallback automático
    languages_to_try = ["por", "eng"]  # Tenta português primeiro, depois inglês
    text = None
    data = None
    
    for lang in languages_to_try:
        try:
            LOGGER.info(f"📖 Tentando OCR com linguagem: {lang}... (timeout: 10 segundos)")
            text = pytesseract.image_to_string(processed_image, lang=lang, timeout=10)
            LOGGER.info(f"📝 Raw OCR text ({lang}): '{text}'")
            
            if text.strip():  # Se conseguiu extrair texto
                # Tenta pegar dados de confiança
                try:
                    data = pytesseract.image_to_data(processed_image, lang=lang, output_type="dict", timeout=10)
                except Exception as conf_err:
                    LOGGER.warning(f"⚠️  Não conseguiu calcular confiança ({lang}): {conf_err}")
                    data = None
                
                break  # Sucesso, sai do loop
        
        except Exception as e:
            LOGGER.warning(f"⚠️  Falha com linguagem '{lang}': {e}")
            if lang == languages_to_try[-1]:  # Última tentativa
                LOGGER.error(f"❌ Tesseract OCR falhou com todas as linguagens: {e}", exc_info=True)
                raise RuntimeError(f"Tesseract failed with all languages") from e
            continue
    
    # Calcula confiança se conseguiu dados
    if data:
        confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
        confidence = sum(confidences) / len(confidences) if confidences else 0
    else:
        confidence = 0
    
    extracted_text = normalize_text(text) if text else ""
    LOGGER.info(f"✅ OCR Success - Text: '{extracted_text}' | Confidence: {confidence:.1f}% | Lang: {lang}")
    
    return VisionResult(text=extracted_text, confidence=confidence)


def crop_image(image: Image.Image, region: tuple[int, int, int, int]) -> Image.Image:
    left, top, width, height = region
    return image.crop((left, top, left + width, top + height))
