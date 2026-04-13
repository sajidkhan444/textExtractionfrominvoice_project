"""Script to run single invoice processing."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dependencies import extractor, qwen_parser
from app.services.file_router import process_invoice_file
from app.services.connection_test_service import test_database_connection, test_storage_connection
from app.utils.console import print_banner, print_separator, print_success, print_error

from google.colab import files
import tempfile
from pathlib import Path


def main():
    print_banner()
    
    print("\n🔌 Testing connections...")    
    test_database_connection()
    test_storage_connection()
    
    print("\n📤 PLEASE UPLOAD YOUR INVOICE IMAGE")
    uploaded = files.upload()
    
    for filename in uploaded.keys():
        print(f"\n📄 PROCESSING: {filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(uploaded[filename])
            tmp_path = tmp_file.name
        
        try:
            result = process_invoice_file(tmp_path, filename, extractor, qwen_parser)
            
            if result.get('type') == 'image' and result['successful'] > 0:
                r = result['results'][0]
                if r['success']:
                    print_success("INVOICE PROCESSED SUCCESSFULLY")
                    print(f"   ID: {r['invoice_id']}")
                    print(f"   Image: {r['image_name']}")
                    print(f"   Company: {r['clean_data'].get('company_name', 'N/A')}")
                    print_separator()
                else:
                    print_error(f"FAILED: {r['error']}")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()