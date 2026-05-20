# app/core/documents_model_loader.py

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import torch
from ultralytics import YOLO
from paddleocr import PaddleOCR

from app.core.documents_config import DocumentsConfig

class DocumentModelLoader:
    """Load and manage all models for document processing"""
    
    _instance = None
    _classifier_model = None
    _deposit_slip_detector = None
    _bank_cheque_detector = None
    _ocr = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def load_classifier(cls):
        """Load document classification model"""
        if cls._classifier_model is None:
            model_path = DocumentsConfig.CLASSIFIER_MODEL_PATH
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Classifier model not found: {model_path}")
            
            print(f"📌 Loading classifier model from: {model_path}")
            cls._classifier_model = YOLO(model_path)
            print("✅ Classifier model loaded")
        
        return cls._classifier_model
    
    @classmethod
    def load_deposit_slip_detector(cls):
        """Load deposit slip detection model"""
        if cls._deposit_slip_detector is None:
            model_path = DocumentsConfig.DEPOSIT_SLIP_DETECTION_MODEL_PATH
            if not os.path.exists(model_path):
                print(f"⚠️ Deposit slip detector not found: {model_path}")
                return None
            
            print(f"📌 Loading deposit slip detector from: {model_path}")
            cls._deposit_slip_detector = YOLO(model_path)
            print("✅ Deposit slip detector loaded")
        
        return cls._deposit_slip_detector
    
    @classmethod
    def load_bank_cheque_detector(cls):
        """Load bank cheque detection model"""
        if cls._bank_cheque_detector is None:
            model_path = DocumentsConfig.BANK_CHEQUE_DETECTION_MODEL_PATH
            if not os.path.exists(model_path):
                print(f"⚠️ Bank cheque detector not found: {model_path}")
                return None
            
            print(f"📌 Loading bank cheque detector from: {model_path}")
            cls._bank_cheque_detector = YOLO(model_path)
            print("✅ Bank cheque detector loaded")
        
        return cls._bank_cheque_detector
    
    @classmethod
    def load_ocr(cls):
        """Load PaddleOCR"""
        if cls._ocr is None:
            print("📌 Loading PaddleOCR...")
            
            os.environ["FLAGS_allocator_strategy"] = "auto_growth"
            
            cls._ocr = PaddleOCR(
                lang=DocumentsConfig.OCR_LANG,
                text_recognition_model_name="PP-OCRv5_server_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=True,
                device="cuda:0" if DocumentsConfig.OCR_USE_GPU else "cpu"
            )
            print("✅ PaddleOCR loaded")
        
        return cls._ocr
    
    @classmethod
    def get_detector_for_type(cls, document_type: str):
        """Get the appropriate detector based on document type"""
        if document_type == "bank_deposit_slip":
            return cls.load_deposit_slip_detector()
        elif document_type == "bank_cheque":
            return cls.load_bank_cheque_detector()
        else:
            raise ValueError(f"No detector for document type: {document_type}")
    
    @classmethod
    def unload_models(cls):
        """Unload all models to free memory"""
        cls._classifier_model = None
        cls._deposit_slip_detector = None
        cls._bank_cheque_detector = None
        cls._ocr = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("Models unloaded and cache cleared")