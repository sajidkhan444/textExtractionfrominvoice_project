"""Script to run single document processing (Image)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import DocumentProcessor
from app.services.document_file_router import process_document_file
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
    
    print("\n📤 PLEASE UPLOAD YOUR DOCUMENT IMAGE")
    uploaded = files.upload()
    
    for filename in uploaded.keys():
        print(f"\n📄 PROCESSING: {filename}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(uploaded[filename])
            tmp_path = tmp_file.name
        
        try:
            # Initialize processor
            processor = DocumentProcessor()
            
            # Process the image
            result = process_document_file(tmp_path, filename, processor, save_crops=False)
            
            if result['type'] == 'image' and result['successful'] > 0:
                r = result['results'][0]
                if r['success']:
                    print_success("DOCUMENT PROCESSED SUCCESSFULLY")
                    print(f"   ID: {r['document_id']}")
                    print(f"   Image: {r['image_name']}")
                    print(f"   Type: {r['document_type']}")
                    print(f"\n   📊 Extracted Data:")
                    for key, value in r['extracted_data'].items():
                        if value:
                            print(f"      {key}: {value}")
                    print_separator()
                else:
                    print_error(f"PROCESSING FAILED: {r.get('error', 'Unknown error')}")
            else:
                print_error("PROCESSING FAILED")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print_error(f"Processing error: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                print("   🧹 Cleaned up temporary file")


if __name__ == "__main__":
    main()