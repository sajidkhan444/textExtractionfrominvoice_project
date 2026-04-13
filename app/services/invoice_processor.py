"""Invoice processing service."""

import json
import os
from app.db.invoice_repository import insert_invoice, get_next_image_name
from app.db.storage_repository import upload_image_to_storage
from app.config import LOCAL_STORAGE_PATH


def process_single_invoice(image_path, image_name, extractor, qwen_parser):
    """Process a single invoice image."""
    print(f"\n{'='*50}")
    print(f"📸 Processing: {image_name}")
    print(f"{'='*50}")
    
    # Extract with EasyOCR
    extracted_data = extractor.process_invoice(image_path)
    if not extracted_data:
        return {'success': False, 'error': 'OCR extraction failed', 'image_name': image_name}
    
    # Parse with Qwen
    clean_data = qwen_parser.process(extracted_data)
    if not clean_data:
        return {'success': False, 'error': 'Qwen parsing failed', 'image_name': image_name}
    
    # Display extracted fields
    print(f"\n📊 EXTRACTED FIELDS:")
    print(f"   Company: {clean_data.get('company_name', 'N/A')}")
    print(f"   Phone: {clean_data.get('phone_number', 'N/A')}")
    print(f"   STRN: {clean_data.get('strn', 'N/A')}")
    print(f"   NTN: {clean_data.get('ntn', 'N/A')}")
    print(f"   Invoice No: {clean_data.get('invoice_number', 'N/A')}")
    print(f"   Date: {clean_data.get('date', 'N/A')}")
    
    # Insert into database
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
    
    if not insert_result['success']:
        return {'success': False, 'error': f'Database insert failed: {insert_result["error"]}', 'image_name': image_name}
    
    # Copy to local storage (permanent)
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