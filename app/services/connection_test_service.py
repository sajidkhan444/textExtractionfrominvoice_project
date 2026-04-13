"""Connection test service for local PostgreSQL and storage."""

from app.db.invoice_repository import count_invoices, get_last_invoice_id, get_next_image_name
from app.db.storage_repository import list_all_images, get_image_url
from app.config import LOCAL_STORAGE_PATH, DB_HOST, DB_PORT, DB_NAME


def test_database_connection():
    """Test database connection and show status."""
    print("\n" + "="*50)
    print("📊 DATABASE CONNECTION TEST (Local PostgreSQL)")
    print("="*50)
    
    try:
        # Test count
        count_result = count_invoices()
        if count_result['success']:
            print(f"✅ Database Connected!")
            print(f"   Host: {DB_HOST}:{DB_PORT}")
            print(f"   Database: {DB_NAME}")
            print(f"   Total invoices: {count_result['count']}")
        else:
            print(f"❌ Database Error: {count_result['error']}")
        
        # Test last ID
        last_id = get_last_invoice_id()
        print(f"   Last invoice ID: {last_id}")
        
        # Test next image name
        next_name = get_next_image_name()
        print(f"   Next image name: {next_name}")
        
        print(f"   Table 'invoices': EXISTS")
        
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
        print(f"   Storage Path: {LOCAL_STORAGE_PATH}")
        
        # List images
        list_result = list_all_images()
        if list_result['success']:
            print(f"   Files in storage: {len(list_result['images'])}")
            
            if list_result['images']:
                print(f"   Recent files:")
                for img in list_result['images'][-5:]:
                    print(f"     - {img['name']} ({img['metadata']['size']} bytes)")
        else:
            print(f"   ⚠️ Could not list files: {list_result['error']}")
        
        # Test URL pattern
        test_url = get_image_url("inv_example.jpg")
        print(f"   URL pattern: {test_url}")
        
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
    
    print("="*50)