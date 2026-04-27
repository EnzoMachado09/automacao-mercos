from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None


@dataclass(slots=True)
class VisionResult:
    text: str
    confidence: float | None = None


def image_digest(image: Image.Image) -> str:
    return sha1(image.tobytes()).hexdigest()


def normalize_text(value: str) -> str:
    cleaned = " ".join(value.replace("\n", " ").replace("\r", " ").split())
    return cleaned.strip()


def ocr_image(image: Image.Image, tesseract_cmd: str | None = None) -> VisionResult:
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    text = pytesseract.image_to_string(image, lang="por")
    return VisionResult(text=normalize_text(text))


def crop_image(image: Image.Image, region: tuple[int, int, int, int]) -> Image.Image:
    left, top, width, height = region
    return image.crop((left, top, left + width, top + height))
