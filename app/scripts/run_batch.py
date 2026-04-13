"""Script to run batch invoice processing."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.dependencies import extractor, qwen_parser
from app.services.file_router import process_invoice_file
from app.services.connection_test_service import test_database_connection, test_storage_connection
from app.utils.console import print_banner, print_separator, print_success

from google.colab import files
import tempfile
from pathlib import Path


def main():
    print_banner()
    
    print("\n🔌 Testing local DB and Storage connections...")    
    test_database_connection()
    test_storage_connection()
    
    print("\n📤 PLEASE UPLOAD YOUR PDF FILE")
    uploaded = files.upload()
    
    for filename in uploaded.keys():
        print(f"\n📄 PROCESSING PDF: {filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(uploaded[filename])
            tmp_path = tmp_file.name
        
        try:
            result = process_invoice_file(tmp_path, filename, extractor, qwen_parser)
            
            if result.get('type') == 'pdf' and result['successful'] > 0:
                print_success("PDF PROCESSING COMPLETE")
                print(f"   Total pages: {result['total']}")
                print(f"   Successful: {result['successful']}")
                print(f"   Failed: {result['failed']}")
                print(f"   Images: inv_{result['start_number']}.jpg to inv_{result['end_number']}.jpg")
                print_separator()
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()