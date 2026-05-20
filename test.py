import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.documents_config import DocumentsConfig
from app.core.documents_model_loader import DocumentModelLoader

def test_config():
    """Test configuration loading"""
    print("\n" + "="*60)
    print("TESTING DOCUMENT PROCESSING CONFIGURATION")
    print("="*60)
    
    # Print config
    DocumentsConfig.print_config()
    
    # Validate paths
    all_exist = DocumentsConfig.validate_paths()
    
    if all_exist:
        print("\n✅ All models found! Configuration is correct.")
    else:
        print("\n❌ Some models missing. Please check paths.")
    
    return all_exist

def test_model_loading():
    """Test model loading"""
    print("\n" + "="*60)
    print("TESTING MODEL LOADING")
    print("="*60)
    
    try:
        # Try loading classifier
        print("\n1. Loading classifier...")
        classifier = DocumentModelLoader.load_classifier()
        print("   ✅ Classifier loaded successfully")
        
        # Try loading deposit slip detector
        print("\n2. Loading deposit slip detector...")
        detector = DocumentModelLoader.load_deposit_slip_detector()
        if detector:
            print("   ✅ Deposit slip detector loaded successfully")
        else:
            print("   ⚠️ Deposit slip detector not found")
        
        # Try loading bank cheque detector
        print("\n3. Loading bank cheque detector...")
        detector = DocumentModelLoader.load_bank_cheque_detector()
        if detector:
            print("   ✅ Bank cheque detector loaded successfully")
        else:
            print("   ⚠️ Bank cheque detector not found")
        
        # Try loading OCR
        print("\n4. Loading PaddleOCR...")
        ocr = DocumentModelLoader.load_ocr()
        print("   ✅ PaddleOCR loaded successfully")
        
        print("\n✅ All models loaded successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error loading models: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 DOCUMENT PROCESSING SYSTEM TEST SUITE")
    print("="*60)
    
    # Run tests
    config_ok = test_config()
    
    if config_ok:
        models_ok = test_model_loading()
    else:
        print("\n⚠️ Skipping model loading due to config issues")
        models_ok = False
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Model Loading: {'✅ PASS' if models_ok else '❌ FAIL'}")
    print("="*60)
