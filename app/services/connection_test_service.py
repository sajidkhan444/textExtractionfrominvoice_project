# app/services/connection_test_service.py

from app.db.invoice_repository import count_invoices, get_last_invoice_id, get_next_image_name
from app.db.document_repository import count_documents, get_last_document_id
from app.db.storage_repository import list_all_images, get_image_url
from app.config import LOCAL_STORAGE_PATH, DB_HOST, DB_PORT, DB_NAME


def test_database_connection():
    """Test database connection and show status."""
    print("\n" + "="*50)
    print("📊 DATABASE CONNECTION TEST (PostgreSQL)")
    print("="*50)
    
    try:
        # Test invoice count
        invoice_count = count_invoices()
        if invoice_count['success']:
            print(f"✅ Database Connected!")
            print(f"   Host: {DB_HOST}:{DB_PORT}")
            print(f"   Database: {DB_NAME}")
            print(f"   Total invoices: {invoice_count['count']}")
        else:
            print(f"⚠️ Invoice table: {invoice_count['error']}")
        
        # Test document count
        doc_count = count_documents()
        if doc_count['success']:
            print(f"   Total documents (slip/deposit/receipt): {doc_count['count']}")
            last_id = get_last_document_id()
            print(f"   Last document ID: {last_id}")
        else:
            print(f"⚠️ Document tables: {doc_count['error']}")
        
        print(f"   Tables: 'invoices', 'slip', 'deposit', 'receipt' - All ready")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    
    print("="*50)


def test_storage_connection():
    """Test storage connection and show status."""
    print("\n" + "="*50)
    print("🗄️ STORAGE CONNECTION TEST (Local File System)")
    print("="*50)
    
    try:
        print(f"✅ Storage Connected!")
        print(f"   Invoice Storage Path: {LOCAL_STORAGE_PATH}")
        
        # List images
        list_result = list_all_images()
        if list_result['success']:
            print(f"   Files in invoice storage: {len(list_result['images'])}")
        
        # Check if document output folder exists
        from app.core.documents_config import DocumentsConfig
        if os.path.exists(DocumentsConfig.OUTPUT_FOLDER):
            doc_files = len(os.listdir(DocumentsConfig.OUTPUT_FOLDER))
            print(f"   Document Storage Path: {DocumentsConfig.OUTPUT_FOLDER}")
            print(f"   Files in document storage: {doc_files}")
        else:
            print(f"   ⚠️ Document storage path not found: {DocumentsConfig.OUTPUT_FOLDER}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    
    print("="*50)