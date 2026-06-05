# app/core/documents_config.py (Add OUTPUT_FOLDER)

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class DocumentsConfig:
    """Configuration for document processing module (Deposit Slips, Cheques, Receipts)"""
    
    # Model paths
    BASE_MODEL_PATH = os.getenv("DOCUMENTS_MODEL_PATH", "app/models")
    
    CLASSIFIER_MODEL_PATH = os.path.join(
        BASE_MODEL_PATH, 
        os.getenv("CLASSIFIER_MODEL", "receipt_classification_model.pt")
    )
    
    DEPOSIT_SLIP_DETECTION_MODEL_PATH = os.path.join(
        BASE_MODEL_PATH,
        os.getenv("DEPOSIT_SLIP_MODEL", "deposit-slip-detection-model-v2.pt")
    )
    
    BANK_CHEQUE_DETECTION_MODEL_PATH = os.path.join(
        BASE_MODEL_PATH,
        os.getenv("BANK_CHEQUE_MODEL", "bankcheckdetection-modelv3.pt")
    )
    
    # Qwen model configuration
    QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
    QWEN_DEVICE = os.getenv("QWEN_DEVICE", "cuda" if __import__('torch').cuda.is_available() else "cpu")
    
    # Processing parameters
    CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.25"))
    IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.7"))
    PADDING = int(os.getenv("PADDING", "10"))
    
    # File paths
    UPLOAD_FOLDER = os.getenv("DOCUMENTS_UPLOAD_FOLDER", "./data/input/documents")
    CROPPED_FOLDER = os.getenv("CROPPED_FOLDER", "./data/temp/cropped_fields")
    RESULTS_FOLDER = os.getenv("DOCUMENTS_RESULTS_FOLDER", "./data/output/documents")
    
    # ADD THIS - Output folder for processed images
    OUTPUT_FOLDER = os.getenv("DOCUMENTS_OUTPUT_FOLDER", "./data/output/documents")
    
    # Convert to absolute paths
    UPLOAD_FOLDER = os.path.abspath(UPLOAD_FOLDER)
    CROPPED_FOLDER = os.path.abspath(CROPPED_FOLDER)
    RESULTS_FOLDER = os.path.abspath(RESULTS_FOLDER)
    OUTPUT_FOLDER = os.path.abspath(OUTPUT_FOLDER)  # ADD THIS
    
    # OCR Configuration
    OCR_LANG = os.getenv("OCR_LANG", "en")
    OCR_USE_GPU = os.getenv("OCR_USE_GPU", "False").lower() == "true"
    
    # Device configuration
    DEVICE = "cuda:0" if __import__('torch').cuda.is_available() else "cpu"
    
    @classmethod
    def ensure_folders(cls):
        """Create necessary folders if they don't exist"""
        folders = [cls.UPLOAD_FOLDER, cls.CROPPED_FOLDER, cls.RESULTS_FOLDER, cls.OUTPUT_FOLDER]
        for folder in folders:
            Path(folder).mkdir(parents=True, exist_ok=True)
            print(f"✅ Folder ready: {folder}")
    
    @classmethod
    def cleanup_cropped_folder(cls):
        """Clean up temporary cropped images after processing"""
        import shutil
        if os.path.exists(cls.CROPPED_FOLDER):
            shutil.rmtree(cls.CROPPED_FOLDER)
            os.makedirs(cls.CROPPED_FOLDER, exist_ok=True)
    
    @classmethod
    def validate_paths(cls):
        """Validate model paths exist"""
        paths = {
            "Classifier": cls.CLASSIFIER_MODEL_PATH,
            "Deposit Slip Detector": cls.DEPOSIT_SLIP_DETECTION_MODEL_PATH,
            "Bank Cheque Detector": cls.BANK_CHEQUE_DETECTION_MODEL_PATH
        }
        
        all_exist = True
        print("\n" + "="*50)
        print("VALIDATING MODEL PATHS")
        print("="*50)
        for name, path in paths.items():
            if not os.path.exists(path):
                print(f"❌ {name} model NOT FOUND at: {path}")
                all_exist = False
            else:
                size = os.path.getsize(path) / (1024 * 1024)
                print(f"✅ {name} model found: {os.path.basename(path)} ({size:.2f} MB)")
        print("="*50)
        
        return all_exist
    
    @classmethod
    def print_config(cls):
        """Print current configuration for debugging"""
        print("\n" + "="*50)
        print("DOCUMENT PROCESSING CONFIGURATION")
        print("="*50)
        print(f"BASE_MODEL_PATH: {cls.BASE_MODEL_PATH}")
        print(f"CLASSIFIER_MODEL_PATH: {cls.CLASSIFIER_MODEL_PATH}")
        print(f"DEPOSIT_SLIP_DETECTION_MODEL_PATH: {cls.DEPOSIT_SLIP_DETECTION_MODEL_PATH}")
        print(f"BANK_CHEQUE_DETECTION_MODEL_PATH: {cls.BANK_CHEQUE_DETECTION_MODEL_PATH}")
        print(f"UPLOAD_FOLDER: {cls.UPLOAD_FOLDER}")
        print(f"CROPPED_FOLDER: {cls.CROPPED_FOLDER}")
        print(f"RESULTS_FOLDER: {cls.RESULTS_FOLDER}")
        print(f"OUTPUT_FOLDER: {cls.OUTPUT_FOLDER}")
        print(f"CONF_THRESHOLD: {cls.CONF_THRESHOLD}")
        print(f"IOU_THRESHOLD: {cls.IOU_THRESHOLD}")
        print(f"PADDING: {cls.PADDING}")
        print(f"DEVICE: {cls.DEVICE}")
        print(f"OCR_USE_GPU: {cls.OCR_USE_GPU}")
        print("="*50)