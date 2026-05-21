# app/services/document_processor.py (COMPLETE FIXED VERSION)

import os
import cv2
import numpy as np
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path

from ultralytics import YOLO
from paddleocr import PaddleOCR

from app.core.documents_config import DocumentsConfig
from app.core.documents_constants import DocumentType
from app.core.documents_model_loader import DocumentModelLoader
from app.ocr.document_ocr import DocumentOCR


def clean_amount_value(amount):
    """Clean amount string to numeric format for database"""
    if amount is None:
        return None
    cleaned = re.sub(r'[^\d\.]', '', str(amount).replace(',', ''))
    try:
        return float(cleaned)
    except:
        return None


def clean_ocr_text(text):
    """Clean common OCR garbage characters and extract only the value"""
    if not text:
        return None
    
    # Remove common garbage characters
    text = re.sub(r'[σ┐â┼áΓÿàαÆÄèââÅ»½♥♠♦♣•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼]', '', text)
    
    # Remove labels with colons
    text = re.sub(r'^[A-Za-z\s]+:\s*', '', text)
    text = re.sub(r'^[A-Za-z\s]+#\s*', '', text)
    
    # Remove special characters but keep letters, numbers, spaces, hyphens
    text = re.sub(r'[^\w\s\-]', '', text)
    
    # Normalize spaces
    text = ' '.join(text.split())
    
    return text.strip()


class DocumentProcessor:
    """Main document processor for cheques, deposit slips, and receipts"""
    
    def __init__(self):
        print("\n" + "="*60)
        print("📄 INITIALIZING DOCUMENT PROCESSOR")
        print("="*60)
        
        self.classifier = None
        self.deposit_slip_detector = None
        self.bank_cheque_detector = None
        self.ocr_manager = None
        self.qwen_parser = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize all models"""
        print("\n📁 Creating folders...")
        DocumentsConfig.ensure_folders()
        print("✅ Folders ready")
        
        print("\n📌 Loading models...")
        
        print("  ├─ Loading classifier...")
        self.classifier = DocumentModelLoader.load_classifier()
        print("  │  ✅ Classifier loaded")
        
        print("  ├─ Loading deposit slip detector...")
        self.deposit_slip_detector = DocumentModelLoader.load_deposit_slip_detector()
        if self.deposit_slip_detector:
            print("  │  ✅ Deposit slip detector loaded")
        else:
            print("  │  ⚠️ Deposit slip detector not found")
        
        print("  ├─ Loading bank cheque detector...")
        self.bank_cheque_detector = DocumentModelLoader.load_bank_cheque_detector()
        if self.bank_cheque_detector:
            print("  │  ✅ Bank cheque detector loaded")
        else:
            print("  │  ⚠️ Bank cheque detector not found")
        
        print("  ├─ Loading OCR...")
        self.ocr_manager = DocumentOCR()
        print("  │  ✅ OCR ready")
        
        print("  └─ Loading Qwen parser...")
        try:
            from app.dependencies import model, tokenizer
            from app.parser.qwen_document_parser import QwenDocumentParser
            self.qwen_parser = QwenDocumentParser(model, tokenizer)
            print("     ✅ Document Qwen parser loaded (reusing existing model)")
        except Exception as e:
            print(f"     ⚠️ Error loading Qwen document parser: {e}")
            self.qwen_parser = None
        
        print("\n" + "="*60)
        print("✅ DOCUMENT PROCESSOR INITIALIZED")
        print("="*60)
    
    def classify_document(self, image_path: str) -> Tuple[str, float]:
        """Classify document type"""
        results = self.classifier(image_path)
        
        if results and len(results) > 0 and results[0].probs is not None:
            probs = results[0].probs
            top1_idx = probs.top1
            confidence = probs.top1conf.item()
            class_name = self.classifier.names[top1_idx]
            
            print(f"\n📊 Classification Probabilities:")
            for idx, prob in enumerate(probs.data.cpu().numpy()):
                if prob > 0.01:
                    print(f"   {self.classifier.names[idx]}: {prob:.2%}")
            
            return class_name, confidence
        
        return "unknown", 0.0
    
    def detect_fields(self, image_path: str, document_type: str) -> Tuple[np.ndarray, List[Dict]]:
        """Detect fields in document"""
        if document_type == "bank_deposit_slip" or document_type == "bank_deposit_slips":
            model = self.deposit_slip_detector
        elif document_type == "bank_cheque":
            model = self.bank_cheque_detector
        else:
            raise ValueError(f"No detector for {document_type}")
        
        if model is None:
            raise ValueError(f"Model not loaded for {document_type}")
        
        image = cv2.imread(image_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = model(image_path, conf=DocumentsConfig.CONF_THRESHOLD, iou=DocumentsConfig.IOU_THRESHOLD)
        
        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            class_names = model.names
            
            for box, cls, conf in zip(boxes, classes, confidences):
                x1, y1, x2, y2 = map(int, box)
                detections.append({
                    'class': class_names[int(cls)],
                    'confidence': float(conf),
                    'bbox': [x1, y1, x2, y2]
                })
        
        detections.sort(key=lambda x: x['bbox'][1])
        return image_rgb, detections
    
    def crop_field(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """Crop detected field with padding"""
        x1, y1, x2, y2 = bbox
        height, width = image.shape[:2]
        
        x1 = max(0, x1 - DocumentsConfig.PADDING)
        y1 = max(0, y1 - DocumentsConfig.PADDING)
        x2 = min(width, x2 + DocumentsConfig.PADDING)
        y2 = min(height, y2 + DocumentsConfig.PADDING)
        
        return image[y1:y2, x1:x2]
    
    def process_pipeline_a(self, image_path: str, document_type: str, save_crops: bool = False) -> Dict:
        """Pipeline A: Detection + Crop + OCR for cheques and deposit slips"""
        image, detections = self.detect_fields(image_path, document_type)
        
        if len(detections) == 0:
            return {"success": False, "error": "No fields detected"}
        
        extracted_data = {}
        
        if save_crops:
            os.makedirs(DocumentsConfig.CROPPED_FOLDER, exist_ok=True)
        
        for det in detections:
            field_name = det['class']
            cropped = self.crop_field(image, det['bbox'])
            
            if save_crops:
                session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                crop_filename = f"{session_id}_{field_name}.jpg"
                crop_path = os.path.join(DocumentsConfig.CROPPED_FOLDER, crop_filename)
                cv2.imwrite(crop_path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
            
            text, confidence = self.ocr_manager.extract_from_crop(cropped, field_name)
            extracted_data[field_name] = text if text else ""
        
        if document_type == "bank_cheque":
            return self._format_cheque_output(extracted_data)
        else:
            return self._format_deposit_slip_output(extracted_data)
    
    def _format_cheque_output(self, extracted_data: Dict) -> Dict:
        """Format extracted data for bank cheque with clean value extraction"""
        output = {"bank_name": None, "pay": None, "iban": None, "check_number": None, "amount": None}
        
        for key, value in extracted_data.items():
            if not value:
                continue
                
            key_lower = key.lower()
            
            if key_lower == "logo":
                cleaned = clean_ocr_text(value)
                output["bank_name"] = cleaned[:30] if cleaned else None
                
            elif key_lower == "pay":
                cleaned = re.sub(r'(?i)^(pay)[:\s]*', '', value)
                cleaned = clean_ocr_text(cleaned)
                output["pay"] = cleaned[:50] if cleaned else None
                
            elif key_lower == "iban":
                cleaned = re.sub(r'\s', '', value)
                cleaned = re.sub(r'[^A-Za-z0-9]', '', cleaned)
                output["iban"] = cleaned[:30] if cleaned else None
                
            elif key_lower in ["checknumber", "chequenumber", "serial"]:
                digits = re.sub(r'\D', '', value)
                output["check_number"] = digits[:20] if digits else None
                
            elif key_lower == "amount":
                output["amount"] = clean_amount_value(value)
        
        print(f"\n📊 CLEAN CHEQUE DATA:")
        for k, v in output.items():
            print(f"   {k}: {v}")
        
        return {"success": True, "document_type": "bank_cheque", "extracted_data": output}
    
    def _format_deposit_slip_output(self, extracted_data: Dict) -> Dict:
        """Format extracted data for deposit slip with clean value extraction"""
        output = {
            "bank_name": None, 
            "account_title": None, 
            "account_number": None,
            "amount": None, 
            "depositor_name": None, 
            "contact_number": None, 
            "cnic": None
        }
        
        for key, value in extracted_data.items():
            if not value:
                continue
                
            key_lower = key.lower()
            
            if key_lower in ["logo", "bank_logo"]:
                cleaned = clean_ocr_text(value)
                output["bank_name"] = cleaned[:30] if cleaned else None
            
            elif key_lower == "account_title":
                cleaned = value
                cleaned = re.sub(r'(?i)^(titleof|account title|accounttitle|card holder name)[:\s]*', '', cleaned)
                cleaned = re.sub(r'[^A-Za-z\s]', '', cleaned)
                cleaned = ' '.join(cleaned.split())
                name_parts = cleaned.split()
                if len(name_parts) >= 2:
                    cleaned = ' '.join(name_parts[:3])
                output["account_title"] = cleaned[:50] if cleaned and len(cleaned) > 2 else None
            
            elif key_lower == "account_number":
                digits = re.sub(r'\D', '', value)
                output["account_number"] = digits[:20] if digits else None
            
            elif key_lower == "amount":
                output["amount"] = clean_amount_value(value)
            
            elif key_lower == "depositor_name":
                cleaned = value
                cleaned = re.sub(r'(?i)^(depositor name|depositorname|depositor)[:\s]*', '', cleaned)
                cleaned = re.sub(r'[^A-Za-z\s]', '', cleaned)
                cleaned = ' '.join(cleaned.split())
                output["depositor_name"] = cleaned[:50] if cleaned and len(cleaned) > 2 else None
            
            elif key_lower == "contact_number":
                digits = re.sub(r'\D', '', value)
                if len(digits) >= 10:
                    if digits.startswith('92'):
                        digits = '0' + digits[2:]
                    elif digits.startswith('3') and len(digits) == 10:
                        digits = '0' + digits
                    if len(digits) > 11:
                        digits = digits[-11:]
                    if len(digits) == 11 and digits.startswith('03'):
                        output["contact_number"] = digits
                    else:
                        output["contact_number"] = None
                else:
                    output["contact_number"] = None
            
            elif key_lower == "cnic":
                digits = re.sub(r'\D', '', value)
                if len(digits) == 13:
                    output["cnic"] = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
                elif len(digits) == 12:
                    output["cnic"] = f"{digits[:4]}-{digits[4:11]}-{digits[11]}"
                else:
                    output["cnic"] = None
        
        print(f"\n📊 CLEAN DEPOSIT SLIP DATA:")
        for k, v in output.items():
            print(f"   {k}: {v}")
        
        return {"success": True, "document_type": "bank_deposit_slips", "extracted_data": output}
    
    def process_pipeline_b(self, image_path: str, save_crops: bool = False) -> Dict:
        """Pipeline B: Full OCR + Qwen for digital receipts"""
        # Get OCR as dictionary (line_XX format)
        ocr_dict = self.ocr_manager.extract_full_document_as_dict(image_path)
        
        if not ocr_dict:
            return {"success": False, "error": "No text extracted"}
        
        if self.qwen_parser:
            # Pass dictionary to Qwen (same format as invoice module)
            extracted_fields = self.qwen_parser.process(ocr_dict)
            
            # Clean amount if present
            if extracted_fields and extracted_fields.get('total_amount'):
                extracted_fields['total_amount'] = clean_amount_value(extracted_fields['total_amount'])
            if extracted_fields and extracted_fields.get('sender_mobile'):
                phone = re.sub(r'\D', '', str(extracted_fields['sender_mobile']))
                extracted_fields['sender_mobile'] = phone[:11] if phone.startswith('03') else None
        else:
            # Fallback
            full_text = self.ocr_manager.extract_full_document(image_path)
            extracted_fields = self._fallback_extraction(full_text)
        
        print(f"\n📊 CLEAN DIGITAL RECEIPT DATA:")
        for k, v in extracted_fields.items():
            if v:
                print(f"   {k}: {v}")
        
        return {"success": True, "document_type": "digital_receipt", "extracted_data": extracted_fields, "full_text": str(ocr_dict)}
    
    def _fallback_extraction(self, text: str) -> Dict:
        """Fallback extraction using regex"""
        extracted = {
            "bank_name": None, "account_title": None, "total_amount": None,
            "ref_id": None, "sender_name": None, "sender_mobile": None,
            "receiver_name": None, "receiver_mobile": None,
            "transaction_date": None, "transaction_time": None
        }
        
        amount_match = re.search(r'(?:Total Amount|Amount|PKR|Rs\.?)[\s:]*([0-9,]+\.?[0-9]*)', text, re.IGNORECASE)
        if amount_match:
            extracted["total_amount"] = clean_amount_value(amount_match.group(1))
        
        ref_match = re.search(r'(?:ID#|Ref#|Transaction ID)[\s:]*([A-Z0-9]+)', text, re.IGNORECASE)
        if ref_match:
            extracted["ref_id"] = ref_match.group(1)
        
        return extracted
    
    def process_document(self, file_path: str, save_crops: bool = False) -> Dict:
        """Main entry point - process any document"""
        doc_type, confidence = self.classify_document(file_path)
        
        print(f"\n{'='*60}")
        print(f"🔍 CLASSIFICATION RESULT")
        print(f"{'='*60}")
        print(f"   Document Type: '{doc_type}'")
        print(f"   Confidence: {confidence:.2%}")
        
        if doc_type == "unknown" or confidence < 0.5:
            return {"success": False, "error": f"Could not classify document: {doc_type}"}
        
        print(f"\n{'='*60}")
        print(f"🚦 ROUTING DECISION")
        print(f"{'='*60}")
        
        if doc_type == "bank_deposit_slips":
            print(f"   ✅ Document is a DEPOSIT SLIP")
            print(f"   🔄 Routing to: PIPELINE A (Detection + Crop + OCR)")
            return self.process_pipeline_a(file_path, "bank_deposit_slip", save_crops=save_crops)
        
        elif doc_type == "bank_cheque":
            print(f"   ✅ Document is a BANK CHEQUE")
            print(f"   🔄 Routing to: PIPELINE A (Detection + Crop + OCR)")
            return self.process_pipeline_a(file_path, "bank_cheque", save_crops=save_crops)
        
        else:
            print(f"   ✅ Document is a DIGITAL RECEIPT")
            print(f"   🔄 Routing to: PIPELINE B (Full OCR + Qwen)")
            return self.process_pipeline_b(file_path, save_crops=save_crops)
    
    # ============================================
    # DETAILED METHODS FOR TESTING API
    # ============================================
    
    def process_pipeline_a_with_details(self, image_path: str, document_type: str, save_crops: bool = False) -> Dict:
        """Pipeline A with detailed debugging information."""
        import time
        
        image, detections = self.detect_fields(image_path, document_type)
        
        if len(detections) == 0:
            return {"success": False, "error": "No fields detected"}
        
        extracted_data = {}
        detection_details = []
        ocr_details = []
        cropped_fields = []
        
        for det in detections:
            field_name = det['class']
            confidence = det['confidence']
            bbox = det['bbox']
            
            cropped = self.crop_field(image, bbox)
            text, ocr_conf = self.ocr_manager.extract_from_crop(cropped, field_name)
            
            detection_details.append({
                "field": field_name,
                "detection_confidence": confidence,
                "bbox": bbox
            })
            
            ocr_details.append({
                "field": field_name,
                "extracted_text": text if text else "",
                "ocr_confidence": ocr_conf
            })
            
            if save_crops:
                crop_filename = f"{os.path.basename(image_path)}_{field_name}.jpg"
                crop_path = os.path.join(DocumentsConfig.CROPPED_FOLDER, crop_filename)
                os.makedirs(DocumentsConfig.CROPPED_FOLDER, exist_ok=True)
                cv2.imwrite(crop_path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                cropped_fields.append({
                    "field": field_name,
                    "path": crop_path
                })
            
            extracted_data[field_name] = text if text else ""
        
        if document_type == "bank_cheque":
            clean_output = self._format_cheque_output(extracted_data)
        else:
            clean_output = self._format_deposit_slip_output(extracted_data)
        
        return {
            "success": True,
            "extracted_data": clean_output["extracted_data"],
            "detection_details": detection_details,
            "ocr_details": ocr_details,
            "cropped_fields": cropped_fields if save_crops else None
        }
    
    def process_pipeline_b_with_details(self, image_path: str, return_ocr_text: bool = False) -> Dict:
        """Pipeline B with detailed debugging information."""
        full_text = self.ocr_manager.extract_full_document(image_path)
        
        if not full_text:
            return {"success": False, "error": "No text extracted"}
        
        if self.qwen_parser:
            # Convert to dictionary format for consistency
            ocr_dict = {"full_text": full_text}
            extracted_fields = self.qwen_parser.process(ocr_dict)
            if extracted_fields and extracted_fields.get('total_amount'):
                extracted_fields['total_amount'] = clean_amount_value(extracted_fields['total_amount'])
        else:
            extracted_fields = self._fallback_extraction(full_text)
        
        result = {"success": True, "extracted_data": extracted_fields}
        
        if return_ocr_text:
            result["full_ocr_text"] = full_text
        
        return result