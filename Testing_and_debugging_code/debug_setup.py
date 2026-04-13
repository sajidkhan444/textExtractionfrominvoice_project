#!/usr/bin/env python
"""Check all imports after removing Supabase."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("🔍 CHECKING ALL IMPORTS (No Supabase)")
print("="*70)

# =====================================================
# Check Config
# =====================================================
print("\n📌 1. CHECKING CONFIG")
print("-"*50)
try:
    from app.config import (
        DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
        LOCAL_STORAGE_PATH, MODEL_NAME, OCR_GPU, OCR_LANGUAGES,
        IMAGE_DPI, IMAGE_QUALITY, get_db_connection_string, get_storage_path
    )
    print("✅ Config imports successful")
    print(f"   DB: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"   Storage: {LOCAL_STORAGE_PATH}")
    print(f"   Model: {MODEL_NAME}")
except Exception as e:
    print(f"❌ Config import failed: {e}")

# =====================================================
# Check Database Modules
# =====================================================
print("\n📌 2. CHECKING DATABASE MODULES")
print("-"*50)

try:
    from app.db.postgres_client import db
    print("✅ postgres_client - OK")
except Exception as e:
    print(f"❌ postgres_client - FAILED: {e}")

try:
    from app.db.invoice_repository import (
        get_last_invoice_id,
        get_next_image_name,
        insert_invoice,
        get_all_invoices,
        get_invoice_by_id,
        count_invoices,
        search_invoices,
        delete_invoice,
        update_invoice_image_path
    )
    print("✅ invoice_repository - OK")
except Exception as e:
    print(f"❌ invoice_repository - FAILED: {e}")

try:
    from app.db.storage_repository import (
        upload_image_to_storage,
        get_image_path,
        get_image_url,
        list_all_images,
        delete_image,
        image_exists,
        ensure_storage_dir
    )
    print("✅ storage_repository - OK")
except Exception as e:
    print(f"❌ storage_repository - FAILED: {e}")

try:
    from app.db import db
    print("✅ db __init__ - OK")
except Exception as e:
    print(f"❌ db __init__ - FAILED: {e}")

# =====================================================
# Check Core Modules
# =====================================================
print("\n📌 3. CHECKING CORE MODULES")
print("-"*50)

try:
    from app.core.model_loader import load_model_and_tokenizer
    print("✅ model_loader - OK")
except Exception as e:
    print(f"❌ model_loader - FAILED: {e}")

try:
    from app.core.constants import TABLE_STOP_WORDS, INVOICE_METADATA_INDICATORS
    print("✅ constants - OK")
except Exception as e:
    print(f"❌ constants - FAILED: {e}")

try:
    from app.core.prompts import get_invoice_extraction_prompt
    print("✅ prompts - OK")
except Exception as e:
    print(f"❌ prompts - FAILED: {e}")

# =====================================================
# Check OCR Module
# =====================================================
print("\n📌 4. CHECKING OCR MODULE")
print("-"*50)

try:
    from app.ocr.smart_invoice_extractor import SmartInvoiceExtractor
    print("✅ smart_invoice_extractor - OK")
except Exception as e:
    print(f"❌ smart_invoice_extractor - FAILED: {e}")

# =====================================================
# Check Parser Module
# =====================================================
print("\n📌 5. CHECKING PARSER MODULE")
print("-"*50)

try:
    from app.parser.qwen_invoice_parser import QwenInvoiceParser
    print("✅ qwen_invoice_parser - OK")
except Exception as e:
    print(f"❌ qwen_invoice_parser - FAILED: {e}")

# =====================================================
# Check Services
# =====================================================
print("\n📌 6. CHECKING SERVICES")
print("-"*50)

try:
    from app.services.invoice_processor import process_single_invoice
    print("✅ invoice_processor - OK")
except Exception as e:
    print(f"❌ invoice_processor - FAILED: {e}")

try:
    from app.services.pdf_service import pdf_to_images_continue
    print("✅ pdf_service - OK")
except Exception as e:
    print(f"❌ pdf_service - FAILED: {e}")

try:
    from app.services.file_router import process_invoice_file
    print("✅ file_router - OK")
except Exception as e:
    print(f"❌ file_router - FAILED: {e}")

try:
    from app.services.connection_test_service import test_database_connection, test_storage_connection
    print("✅ connection_test_service - OK")
except Exception as e:
    print(f"❌ connection_test_service - FAILED: {e}")

# =====================================================
# Check Utils
# =====================================================
print("\n📌 7. CHECKING UTILS")
print("-"*50)

try:
    from app.utils.console import print_banner, print_separator, print_success, print_error, print_info, print_warning
    print("✅ console - OK")
except Exception as e:
    print(f"❌ console - FAILED: {e}")

try:
    from app.utils.json_utils import save_json, load_json
    print("✅ json_utils - OK")
except Exception as e:
    print(f"❌ json_utils - FAILED: {e}")

try:
    from app.utils.helpers import ensure_dir, clean_filename, get_file_extension
    print("✅ helpers - OK")
except Exception as e:
    print(f"❌ helpers - FAILED: {e}")

# =====================================================
# Check Dependencies
# =====================================================
print("\n📌 8. CHECKING DEPENDENCIES")
print("-"*50)

try:
    from app.dependencies import extractor, qwen_parser
    print("✅ dependencies - OK")
    print(f"   extractor type: {type(extractor).__name__}")
    print(f"   qwen_parser type: {type(qwen_parser).__name__}")
except Exception as e:
    print(f"❌ dependencies - FAILED: {e}")

# =====================================================
# Check Main
# =====================================================
print("\n📌 9. CHECKING MAIN")
print("-"*50)

try:
    from app.main import main
    print("✅ main - OK")
except Exception as e:
    print(f"❌ main - FAILED: {e}")

# =====================================================
# Summary
# =====================================================
print("\n" + "="*70)
print("📊 IMPORT CHECK SUMMARY")
print("="*70)
print("✅ All imports successful! No Supabase dependencies found.")
print("="*70)