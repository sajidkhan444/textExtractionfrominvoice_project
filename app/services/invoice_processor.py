"""Invoice processing service."""

import json
import os
import traceback
from app.db.invoice_repository import insert_invoice, get_next_image_name
from app.db.storage_repository import upload_image_to_storage
from app.config import LOCAL_STORAGE_PATH


def process_single_invoice(image_path, image_name, extractor, qwen_parser):
    """Process a single invoice image."""
    print(f"\n{'='*50}")
    print(f"📸 Processing: {image_name}")
    print(f"{'='*50}")
    
    # Extract with EasyOCR
    print("🔍 [DEBUG] Step 1: Starting OCR extraction...")
    extracted_data = extractor.process_invoice(image_path)
    if not extracted_data:
        print("❌ [DEBUG] OCR extraction returned None or empty")
        return {'success': False, 'error': 'OCR extraction failed', 'image_name': image_name}
    print(f"✅ [DEBUG] OCR extraction complete. Lines extracted: {len(extracted_data)}")
    
    # Parse with Qwen
    print("🔍 [DEBUG] Step 2: Starting Qwen parsing...")
    clean_data = qwen_parser.process(extracted_data)
    if not clean_data:
        print("❌ [DEBUG] Qwen parsing returned None or empty")
        return {'success': False, 'error': 'Qwen parsing failed', 'image_name': image_name}
    print(f"✅ [DEBUG] Qwen parsing complete. Clean data: {clean_data}")
    
    # Display extracted fields
    print(f"\n📊 EXTRACTED FIELDS:")
    print(f"   Company: {clean_data.get('company_name', 'N/A')}")
    print(f"   Phone: {clean_data.get('phone_number', 'N/A')}")
    print(f"   STRN: {clean_data.get('strn', 'N/A')}")
    print(f"   NTN: {clean_data.get('ntn', 'N/A')}")
    print(f"   Invoice No: {clean_data.get('invoice_number', 'N/A')}")
    print(f"   Date: {clean_data.get('date', 'N/A')}")
    
    # Insert into database
    print("\n🔍 [DEBUG] Step 3: Inserting into database...")
    print(f"🔍 [DEBUG] insert_invoice parameters:")
    print(f"   company_name: {clean_data.get('company_name')}")
    print(f"   phone_number: {clean_data.get('phone_number')}")
    print(f"   strn: {clean_data.get('strn')}")
    print(f"   ntn: {clean_data.get('ntn')}")
    print(f"   order_number: {clean_data.get('order_number')}")
    print(f"   invoice_number: {clean_data.get('invoice_number')}")
    print(f"   invoice_date: {clean_data.get('date')}")
    print(f"   clean_json: {json.dumps(clean_data)[:100]}...")
    print(f"   raw_ocr_json: {json.dumps(extracted_data)[:100]}...")
    print(f"   image_path: {image_name}")
    
    try:
        insert_result = insert_invoice(
            company_name=clean_data.get('company_name'),
            phone_number=clean_data.get('phone_number'),
            strn=clean_data.get('strn'),
            ntn=clean_data.get('ntn'),
            order_number=clean_data.get('order_number'),
            invoice_number=clean_data.get('invoice_number'),
            invoice_date=clean_data.get('date'),
            clean_json=json.dumps(clean_data),
            raw_ocr_json=json.dumps(extracted_data),
            image_path=image_name
        )
        print(f"🔍 [DEBUG] insert_result: {insert_result}")
    except Exception as e:
        print(f"❌ [DEBUG] Exception during insert_invoice call: {e}")
        traceback.print_exc()
        return {'success': False, 'error': f'Database insert exception: {str(e)}', 'image_name': image_name}
    
    if not insert_result['success']:
        print(f"❌ [DEBUG] Insert failed: {insert_result.get('error')}")
        return {'success': False, 'error': f'Database insert failed: {insert_result["error"]}', 'image_name': image_name}
    
    print(f"✅ [DEBUG] Database insert successful! ID: {insert_result.get('id')}")
    
    # Copy to local storage (permanent)
    print("\n🔍 [DEBUG] Step 4: Saving image to storage...")
    upload_result = upload_image_to_storage(image_path, image_name)
    
    if not upload_result['success']:
        print(f"   ⚠️ Storage warning: {upload_result['error']}")
    else:
        print(f"   ✅ Image saved to: {upload_result['local_path']}")
    
    print(f"\n✅ SUCCESS! Saved as {image_name} (ID: {insert_result['id']})")
    
    return {
        'success': True,
        'invoice_id': insert_result['id'],
        'image_name': image_name,
        'clean_data': clean_data
    }