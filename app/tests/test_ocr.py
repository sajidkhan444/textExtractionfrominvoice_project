"""Test OCR functionality."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ocr.smart_invoice_extractor import SmartInvoiceExtractor


def test_ocr_initialization():
    """Test OCR extractor initialization."""
    extractor = SmartInvoiceExtractor()
    assert extractor is not None
    assert extractor.reader is not None
    print("✅ OCR test passed!")


if __name__ == "__main__":
    test_ocr_initialization()