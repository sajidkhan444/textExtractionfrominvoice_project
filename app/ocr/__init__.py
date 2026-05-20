# app/ocr/__init__.py

from app.ocr.document_ocr import DocumentOCR
from app.ocr.ocr_loader import get_ocr

__all__ = ['DocumentOCR', 'get_ocr']