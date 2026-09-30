import logging
import os
from pathlib import Path

from fastapi import UploadFile
# import paddlex as px

from ocr.config import LOGGER_NAME
from ocr.normalize_image import normalize_image

logger = logging.getLogger(LOGGER_NAME)

def _get_model_dir(*segments: str) -> str:
    base_dir = Path(os.environ.get("PADDLE_OCR_BASE_DIR", Path.home() / ".paddleocr"))
    target = base_dir.joinpath(*segments)
    target.mkdir(parents=True, exist_ok=True)
    return str(target)

def extract_text_with_ocr(file: UploadFile):
    """
        Extracts text from an image using PaddleOCR CPU

        Passes a normalized image into the OCR model and then returns extracted information in the form of a list

        Args:
            file (UploadFile): A file uploaded by the frontend through fastAPI

        Returns:
            A List of text, confidence score pairs

        """

    #Call OCR and pass in pre-downloaded models, language and set to CPU mode
    logger.info("AAA")
    det_model_dir = _get_model_dir("whl", "det", "en", "en_PP-OCRv3_det_infer")
    rec_model_dir = _get_model_dir("whl", "rec", "en", "en_PP-OCRv3_rec_infer")

    '''
    logger.info("BBB")
    detector = px.create_model(
        model_name="PP-OCRv3_mobile_det",
        model_dir=det_model_dir,
        device='cpu'
    )

    logger.info("CCC")
    recognizer = px.create_model(
        model_name="PP-OCRv3_mobile_rec",
        model_dir=rec_model_dir,
        device='cpu'
    )

    logger.info("DDD")
    #Normalize file for OCR processing
    image = normalize_image(file)

    if image is None:
        return None

    logger.info("EEE")
    det_res = list(detector.predict(image))
    
    logger.info("FFF")
    rec_res = list(recognizer.predict(image))
    
    return det_res, rec_res
    '''
    return
