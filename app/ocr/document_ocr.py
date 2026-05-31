# app/ocr/document_ocr.py - Add PDF guard

import cv2
import re
import numpy as np
from typing import Tuple, Dict
from paddleocr import PaddleOCR

class DocumentOCR:
    """OCR handler for document processing"""
    
    def __init__(self):
        self.ocr = None
        self._load_ocr()
    
    def _load_ocr(self):
        """Load PaddleOCR 2.x with working configuration"""
        try:
            import os
            
            print("📌 Loading PaddleOCR for documents...")
            os.environ["FLAGS_allocator_strategy"] = "auto_growth"
            
            self.ocr = PaddleOCR(
                lang='en',
                text_recognition_model_name="PP-OCRv5_server_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
                device="cpu"
            )
            print("✅ PaddleOCR ready")
        except Exception as e:
            print(f"⚠️ Failed to load PaddleOCR: {e}")
            self.ocr = None
    
    def _is_pdf(self, file_path: str) -> bool:
        """Check if file path is a PDF"""
        return file_path.lower().endswith('.pdf')
    
    def extract_full_document_as_dict(self, image_path: str) -> Dict:
        """Extract all text and return as dictionary with line_XX format"""
        # Guard: Do not process PDFs directly
        if self._is_pdf(image_path):
            print(f"❌ ERROR: PDF file passed to extract_full_document_as_dict: {image_path}")
            print("   PDF files must be converted to images first!")
            return {}
        
        if self.ocr is None:
            return {}
        
        try:
            result = self.ocr.predict(image_path)
            
            if result and len(result) > 0 and isinstance(result[0], dict):
                texts = result[0].get('rec_texts', [])
                
                ocr_dict = {}
                for idx, text in enumerate(texts, start=1):
                    ocr_dict[f"line_{idx:02d}"] = text.strip() if text else ""
                
                print(f"📝 Extracted {len(texts)} lines of text")
                return ocr_dict
            
            return {}
            
        except Exception as e:
            print(f"OCR Error in extract_full_document_as_dict: {e}")
            return {}
    
    def extract_full_document(self, image_path: str) -> str:
        """Extract all text as raw string"""
        # Guard: Do not process PDFs directly
        if self._is_pdf(image_path):
            print(f"❌ ERROR: PDF file passed to extract_full_document: {image_path}")
            print("   PDF files must be converted to images first!")
            return ""
        
        if self.ocr is None:
            return ""
        
        try:
            result = self.ocr.predict(image_path)
            
            if result and len(result) > 0 and isinstance(result[0], dict):
                texts = result[0].get('rec_texts', [])
                if texts:
                    full_text = ' '.join(texts)
                    print(f"📝 Extracted {len(full_text)} characters")
                    return full_text
            return ""
        except Exception as e:
            print(f"OCR Error in extract_full_document: {e}")
            return ""
    
    def extract_from_crop(self, cropped_image: np.ndarray, field_name: str = "") -> Tuple[str, float]:
        """Extract text from cropped image"""
        if self.ocr is None or cropped_image is None or cropped_image.size == 0:
            return "", 0.0

        # Convert to RGB if needed
        if len(cropped_image.shape) == 2:
            cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2RGB)
        elif cropped_image.shape[2] == 4:
            cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_RGBA2RGB)

        try:
            result = self.ocr.predict(cropped_image)

            if result and len(result) > 0 and isinstance(result[0], dict):
                texts = result[0].get('rec_texts', [])
                scores = result[0].get('rec_scores', [])

                if texts:
                    full_text = ' '.join(texts)
                    avg_confidence = sum(scores) / len(scores) if scores else 0.0
                    full_text = self._postprocess_text(full_text, field_name)
                    return full_text, avg_confidence

            return "", 0.0

        except Exception as e:
            print(f"OCR Error in extract_from_crop: {e}")
            return "", 0.0
    
    def _postprocess_text(self, text: str, field_name: str) -> str:
        """Post-process extracted text based on field type"""
        text = ' '.join(text.split())
        text = re.sub(r'[^\w\s\.\,\-\*\:]', '', text)
        
        field_lower = field_name.lower()
        
        if 'amount' in field_lower:
            amount_pattern = r'[\d\.,]+'
            amounts = re.findall(amount_pattern, text)
            if amounts:
                text = max(amounts, key=len)
        
        elif 'checknumber' in field_lower or 'cheque' in field_lower or 'serial' in field_lower:
            num_pattern = r'\d+'
            numbers = re.findall(num_pattern, text)
            if numbers:
                text = ''.join(numbers)
        
        elif 'cnic' in field_lower:
            cnic_pattern = r'\d{5}-\d{7}-\d{1}'
            matches = re.findall(cnic_pattern, text)
            if matches:
                text = matches[0]
            else:
                num_pattern = r'\d+'
                numbers = re.findall(num_pattern, text)
                if numbers:
                    text = ''.join(numbers)
        
        elif 'account' in field_lower and 'title' not in field_lower:
            num_pattern = r'\d+'
            numbers = re.findall(num_pattern, text)
            if numbers:
                text = ''.join(numbers)
        
        return text.strip()