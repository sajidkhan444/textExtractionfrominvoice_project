# app/ocr/ocr_loader.py

import os
from paddleocr import PaddleOCR

_ocr_instance = None

def get_ocr():
    """Get or create a singleton OCR instance"""
    global _ocr_instance
    if _ocr_instance is None:
        print("📌 Initializing PaddleOCR...")
        os.environ["FLAGS_allocator_strategy"] = "auto_growth"
        _ocr_instance = PaddleOCR(
            lang='en',
            text_recognition_model_name="PP-OCRv5_server_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            device="cpu"
        )
        print("✅ PaddleOCR ready")
    return _ocr_instance