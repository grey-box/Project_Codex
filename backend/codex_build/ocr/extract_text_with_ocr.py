import logging
from fastapi import UploadFile
import easyocr

from ocr.config import LOGGER_NAME
from ocr.normalize_image import normalize_image

logger = logging.getLogger(LOGGER_NAME)

# Initialize EasyOCR Reader once globally
reader = easyocr.Reader(['en'], gpu=False)

def extract_text_with_ocr(file: UploadFile):
    image = normalize_image(file)

    if image is None:
        return None

    try:
        file.file.seek(0)
        
        results = reader.readtext(image)

        extracted_texts = []
        for bbox, text, score in results:
            if (float(score) > 0.9):
                extracted_texts.append({
                    "rec_text": text,
                    "rec_score": float(score)
                })

        return extracted_texts

    except Exception as e:
        logger.error(f"[EXCEPTION] EasyOCR failed: {e}")
        raise e