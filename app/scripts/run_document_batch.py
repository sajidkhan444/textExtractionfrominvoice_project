"""Script to run batch document processing (PDF)."""

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
    
    print("\n🔌 Testing database and storage connections...")    
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
            # Initialize processor
            processor = DocumentProcessor()
            
            # Process the PDF
            result = process_document_file(tmp_path, filename, processor, save_crops=False)
            
            if result['type'] == 'pdf' and result['successful'] > 0:
                print_success("PDF PROCESSING COMPLETE")
                print(f"   Total pages: {result['total']}")
                print(f"   ✅ Successful: {result['successful']}")
                print(f"   ❌ Failed: {result['failed']}")
                
                # List successfully processed documents
                print(f"\n   📸 Successfully processed pages:")
                for idx, res in enumerate(result['results']):
                    if res['success']:
                        print(f"      Page {idx+1}: {res['image_name']} ({res['document_type']})")
                print_separator()
            else:
                print_error("PDF PROCESSING FAILED")
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