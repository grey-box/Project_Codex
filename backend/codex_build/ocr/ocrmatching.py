import logging
from typing import List

from fastapi import APIRouter, HTTPException, status, UploadFile, File

import ocr.schemas as schemas
from ocr.config import LOGGER_NAME
from ocr.extract_text_with_ocr import extract_text_with_ocr
from ocr.scan_and_clean_uploadfile import scan_and_clean_uploadfile

router = APIRouter(prefix="/ocrmatching", tags=["ocrmatching"])
logger = logging.getLogger(LOGGER_NAME)

@router.post("/", response_model=List[schemas.OCRExtractionResult], status_code=status.HTTP_200_OK)
async def ocr_matching_endpoint(
    file: UploadFile = File(...),
) -> List[schemas.OCRExtractionResult]:
    try:
        cleaned_file = scan_and_clean_uploadfile(file)
        if cleaned_file is not None:
            extracted_texts = extract_text_with_ocr(cleaned_file)
            return extracted_texts

        logger.error("Could Not Read File")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded image file."
        )

    except HTTPException:
        raise
    except Exception as e:
        error_message = f"Error performing OCR extraction: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )