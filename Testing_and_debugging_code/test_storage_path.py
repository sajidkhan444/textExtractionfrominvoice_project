import os
from dotenv import load_dotenv

load_dotenv()

storage_path = os.getenv("LOCAL_STORAGE_PATH")
print(f"Storage path from .env: {storage_path}")

# Check if exists
if os.path.exists(storage_path):
    print(f"✅ Folder exists: {storage_path}")
    
    # List existing invoices
    files = [f for f in os.listdir(storage_path) if f.endswith('.jpg')]
    print(f"📸 Existing invoice images: {len(files)}")
    for f in files[:5]:
        print(f"   - {f}")
else:
    print(f"❌ Folder does not exist. Creating it...")
    os.makedirs(storage_path, exist_ok=True)
    print(f"✅ Created folder: {storage_path}")