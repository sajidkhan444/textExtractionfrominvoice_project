# app/ocr/document_ocr.py - Modified to return dictionary format

import cv2
import re
import numpy as np
from typing import Tuple, Dict

class DocumentOCR:
    """OCR handler for document processing - returns dictionary format like EasyOCR"""
    
    def __init__(self):
        self.ocr = None
        self._load_ocr()
    
    def _load_ocr(self):
        """Load PaddleOCR"""
        try:
            import os
            from paddleocr import PaddleOCR
            
            print("📌 Loading PaddleOCR for documents...")
            os.environ["FLAGS_allocator_strategy"] = "auto_growth"
            
            self.ocr = PaddleOCR(
                lang='en',
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
                device="cpu",
                show_log=False
            )
            print("✅ PaddleOCR ready")
        except Exception as e:
            print(f"⚠️ Failed to load PaddleOCR: {e}")
            self.ocr = None
    
    def extract_full_document_as_dict(self, image_path: str) -> Dict:
        """
        Extract all text and return as dictionary with line_XX format
        (Same format as EasyOCR invoice module)
        """
        if self.ocr is None:
            return {}
        
        try:
            result = self.ocr.ocr(image_path, cls=True)
            
            if result and len(result) > 0:
                texts = []
                for line in result[0]:
                    if len(line) >= 2:
                        texts.append(line[1][0])
                
                # Convert to dictionary with line_XX format (same as EasyOCR)
                ocr_dict = {}
                for idx, text in enumerate(texts, start=1):
                    ocr_dict[f"line_{idx:02d}"] = text
                
                return ocr_dict
            
            return {}
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return {}
    
    # Keep old method for backward compatibility
    def extract_full_document(self, image_path: str) -> str:
        """Extract all text as raw string (for fallback)"""
        if self.ocr is None:
            return ""
        
        try:
            result = self.ocr.ocr(image_path, cls=True)
            
            if result and len(result) > 0:
                texts = []
                for line in result[0]:
                    if len(line) >= 2:
                        texts.append(line[1][0])
                return ' '.join(texts)
            return ""
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def extract_from_crop(self, cropped_image: np.ndarray, field_name: str = "") -> Tuple[str, float]:
        """Extract text from cropped image"""
        if self.ocr is None or cropped_image is None or cropped_image.size == 0:
            return "", 0.0

        if len(cropped_image.shape) == 2:
            cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2RGB)
        elif cropped_image.shape[2] == 4:
            cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_RGBA2RGB)

        try:
            result = self.ocr.ocr(cropped_image, cls=True)
            
            if result and len(result) > 0:
                texts = []
                scores = []
                for line in result[0]:
                    if len(line) >= 2:
                        texts.append(line[1][0])
                        scores.append(line[1][1])
                
                if texts:
                    full_text = ' '.join(texts)
                    avg_confidence = sum(scores) / len(scores) if scores else 0.0
                    full_text = self._postprocess_text(full_text, field_name)
                    return full_text, avg_confidence
            
            return "", 0.0

        except Exception as e:
            print(f"OCR Error: {e}")
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