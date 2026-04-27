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
    try:
        LOGGER.info("📖 Running Tesseract OCR with lang=por... (timeout: 10 segundos)")
        
        # Salva temporariamente a imagem processada para OCR
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            processed_image.save(tmp_path)
        
        try:
            # Tenta com timeout de 10 segundos
            LOGGER.info(f"   Tesseract command: {tesseract_cmd or 'default'}")
            text = pytesseract.image_to_string(processed_image, lang="por", timeout=10)
            LOGGER.info(f"📝 Raw OCR text: '{text}'")
            
            # Tenta pegar dados de confiança
            try:
                data = pytesseract.image_to_data(processed_image, lang="por", output_type="dict", timeout=10)
                confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
                confidence = sum(confidences) / len(confidences) if confidences else 0
            except Exception as conf_err:
                LOGGER.warning(f"⚠️  Não conseguiu calcular confiança: {conf_err}")
                confidence = 0
            
            extracted_text = normalize_text(text)
            LOGGER.info(f"✅ OCR Success - Text: '{extracted_text}' | Confidence: {confidence:.1f}%")
            
            return VisionResult(text=extracted_text, confidence=confidence)
        
        finally:
            # Limpa arquivo temporário
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except:
                pass
    
    except subprocess.TimeoutExpired:
        LOGGER.error("❌ Tesseract TIMEOUT - tomou mais de 10 segundos (pode estar travado)")
        raise RuntimeError("Tesseract timeout - try manually entering name")
    except Exception as e:
        LOGGER.error(f"❌ Tesseract OCR error: {e}", exc_info=True)
        raise


def crop_image(image: Image.Image, region: tuple[int, int, int, int]) -> Image.Image:
    left, top, width, height = region
    return image.crop((left, top, left + width, top + height))
