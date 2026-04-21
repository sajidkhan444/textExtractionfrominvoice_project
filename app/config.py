"""Configuration management."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =====================================================
# DATABASE CONFIGURATION
# =====================================================

# Local PostgreSQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "expenses_flow")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# =====================================================
# STORAGE CONFIGURATION
# =====================================================

# Processed Invoices Path (inside project)
PROCESSED_INVOICES_PATH = os.getenv("PROCESSED_INVOICES_PATH", "./data/processed_invoices")

# Ensure the storage path exists
if PROCESSED_INVOICES_PATH:
    PROCESSED_INVOICES_PATH = os.path.abspath(PROCESSED_INVOICES_PATH)
    os.makedirs(PROCESSED_INVOICES_PATH, exist_ok=True)
# =====================================================
# MODEL CONFIGURATION
# =====================================================

MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-3B-Instruct")

# =====================================================
# OCR CONFIGURATION
# =====================================================

OCR_GPU = os.getenv("OCR_GPU", "False").lower() == "true"
OCR_LANGUAGES = ['en']

# =====================================================
# IMAGE CONFIGURATION
# =====================================================

IMAGE_DPI = int(os.getenv("IMAGE_DPI", "200"))
IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "90"))

# =====================================================
# FILE PROCESSING CONFIGURATION
# =====================================================

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
SUPPORTED_PDF_EXTENSION = ['.pdf']

# Temporary file settings
TEMP_DIR = os.getenv("TEMP_DIR", "./data/temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Local storage path alias for backwards compatibility
LOCAL_STORAGE_PATH = PROCESSED_INVOICES_PATH

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_db_connection_string():
    """Get PostgreSQL connection string."""
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_storage_path():
    """Get the local storage path for invoice images."""
    return LOCAL_STORAGE_PATH

def print_config():
    """Print current configuration."""
    print("\n" + "="*50)
    print("📋 CONFIGURATION SUMMARY")
    print("="*50)
    print(f"   DB: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"   Storage: {LOCAL_STORAGE_PATH}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   OCR GPU: {OCR_GPU}")
    print(f"   Image DPI: {IMAGE_DPI}")
    print("="*50 + "\n")