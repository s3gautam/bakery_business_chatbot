import io

import pytesseract
from PIL import Image


def extract_text(image_bytes: bytes) -> str:
    """OCR a payment screenshot to plain text using Tesseract. Requires
    the `tesseract-ocr` system binary (see packages.txt for Streamlit
    Cloud, or `apt install tesseract-ocr` locally).
    """
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)
