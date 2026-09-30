"""

OCR Matching Router Module.

This module provides API endpoints for OCR operations, which allows extracting text from image files
then finding approximate matches for most medical terms in the database from extracted text.
"""

import logging
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

import ocr.schemas as schemas
from ocr.config import LOGGER_NAME
from ocr.schemas import FuzzyMatching, FuzzyResult
from ocr.extract_text_with_ocr import extract_text_with_ocr

from ocr.scan_and_clean_uploadfile import scan_and_clean_uploadfile

#Initialize router with prefix and tags for API documentation
router= APIRouter(prefix="/ocrmatching", tags=["ocrmatching"])

#Set up logger for this module
logger = logging.getLogger(LOGGER_NAME)

@router.post("/", response_model=schemas.FuzzyMatching, status_code=status.HTTP_201_CREATED)
async def ocr_matching_endpoint(
        file:UploadFile = File(...),
        ) -> schemas.FuzzyMatching:
    try:
        cleaned_file = scan_and_clean_uploadfile(file)
        if cleaned_file is not None:
            extracted_texts = extract_text_with_ocr(cleaned_file)
            return extracted_texts

        logger.error("Could Not Read File")
        return None

    except Exception as e:
        error_message = f"Error performing OCR extraction: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )

