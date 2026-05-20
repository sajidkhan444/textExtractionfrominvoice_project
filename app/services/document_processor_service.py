# app/services/document_processor_service.py

import os
import tempfile
from pathlib import Path
from app.services.document_processor import DocumentProcessor, clean_amount_value
from app.db.document_repository import (
    get_last_document_id, 
    get_next_document_name,
    insert_cheque_document,
    insert_deposit_slip_document,
    insert_digital_receipt_document
)
from app.db.document_storage_repository import save_processed_image


# In process_single_document_page, generate different names based on document type:

def process_single_document_page(image_path, image_name, document_processor, save_crops=False):
    """Process a single document image page."""
    print(f"\n{'='*50}")
    print(f"📄 Processing: {image_name}")
    print(f"{'='*50}")
    
    # Process the document
    result = document_processor.process_document(image_path, save_crops=save_crops)
    
    if not result.get('success'):
        return {
            'success': False, 
            'error': result.get('error', 'Processing failed'), 
            'image_name': image_name
        }
    
    extracted_data = result.get('extracted_data', {})
    document_type = result.get('document_type', 'unknown')
    full_text = result.get('full_text', '')
    
    print(f"\n📋 Document Type: {document_type}")
    print(f"📋 Extracted data: {extracted_data}")
    
    # Generate permanent image name based on document type
    from app.db.document_repository import (
        get_next_cheque_name,
        get_next_deposit_name,
        get_next_receipt_name
    )
    
    if document_type == 'bank_cheque':
        permanent_name = get_next_cheque_name()
    elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
        permanent_name = get_next_deposit_name()
    else:
        permanent_name = get_next_receipt_name()
    
    print(f"📸 Assigned permanent name: {permanent_name}")
    
    # Save the processed image with permanent name
    from app.db.document_storage_repository import save_processed_image
    save_result = save_processed_image(image_path, permanent_name)
    
    if not save_result['success']:
        print(f"   ⚠️ Failed to save image: {save_result['error']}")
        image_filename = permanent_name
    else:
        image_filename = save_result['filename']
        print(f"   ✅ Image saved as: {image_filename}")
    
    # Insert based on document type
    if document_type == 'bank_cheque':
        print(f"💾 Inserting into SLIP table (BANK CHEQUE)")
        from app.db.document_repository import insert_cheque_document
        insert_result = insert_cheque_document(
            bank_cheque_name=extracted_data.get('bank_name'),
            account_holder_name=extracted_data.get('pay'),
            cheque_number=extracted_data.get('check_number'),
            iban=extracted_data.get('iban'),
            cheque_amount=extracted_data.get('amount'),
            cheque_image_filename=image_filename
        )
        
    elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
        print(f"💾 Inserting into DEPOSIT table")
        from app.db.document_repository import insert_deposit_slip_document
        insert_result = insert_deposit_slip_document(
            bank_deposit_name=extracted_data.get('bank_name'),
            account_title=extracted_data.get('account_title'),
            account_number=extracted_data.get('account_number'),
            depositor_name=extracted_data.get('depositor_name'),
            contact_number=extracted_data.get('contact_number'),
            cnic=extracted_data.get('cnic'),
            deposit_amount=extracted_data.get('amount'),
            deposit_image_filename=image_filename,
            serial_number=extracted_data.get('serial_number')  # If you have serial number
        )
        
    else:  # digital_receipt
        print(f"💾 Inserting into RECEIPT table")
        from app.db.document_repository import insert_digital_receipt_document
        insert_result = insert_digital_receipt_document(
            bank_digital_name=extracted_data.get('bank_name'),
            digital_amount=extracted_data.get('total_amount'),
            sender_name=extracted_data.get('sender_name'),
            receiver_name=extracted_data.get('receiver_name'),
            reference_id=extracted_data.get('ref_id'),
            phone_number=extracted_data.get('sender_mobile'),
            payment_date=extracted_data.get('transaction_date'),
            payment_time=extracted_data.get('transaction_time'),
            digital_image_filename=image_filename
        )
    
    if not insert_result['success']:
        return {
            'success': False, 
            'error': f'Database insert failed: {insert_result["error"]}', 
            'image_name': image_name
        }
    
    print(f"\n✅ SUCCESS! Saved as {permanent_name} (ID: {insert_result['id']})")
    
    return {
        'success': True,
        'document_id': insert_result['id'],
        'image_name': permanent_name,
        'document_type': document_type,
        'extracted_data': extracted_data
    }


# app/services/document_processor_service.py

def process_document_file(file_path, filename, document_processor, save_crops=False):
    """Main entry point - handles both single images and PDFs for documents."""
    file_ext = Path(filename).suffix.lower()
    
    # CASE 1: Single Image File
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print("🖼️ Detected: Single Image File")
        
        document_name = get_next_document_name()
        print(f"📸 Assigned document name: {document_name}")
        
        result = process_single_document_page(file_path, document_name, document_processor, save_crops=save_crops)
        
        return {
            'type': 'image',
            'total': 1,
            'successful': 1 if result['success'] else 0,
            'failed': 0 if result['success'] else 1,
            'results': [result]
        }
    
    # CASE 2: PDF File
    elif file_ext == '.pdf':
        print("📚 Detected: PDF File (Multi-page)")
        
        from app.services.document_pdf_service import pdf_to_document_images_continue
        
        last_id = get_last_document_id()
        start_number = last_id + 1
        
        print(f"\n📊 Database Status:")
        print(f"   Last document ID: {last_id}")
        print(f"   Starting from: payment_slip_{start_number}.jpg")
        
        print(f"\n🔄 Converting PDF to images...")
        image_paths = pdf_to_document_images_continue(file_path, start_from=start_number)
        
        if not image_paths:
            return {'type': 'pdf', 'total': 0, 'successful': 0, 'failed': 0, 'error': 'PDF conversion failed'}
        
        results = []
        for idx, image_path in enumerate(image_paths):
            current_number = start_number + idx
            document_name = f"payment_slip_{current_number}.jpg"
            
            print(f"\n📄 Processing page {idx+1}/{len(image_paths)}: {document_name}")
            
            result = process_single_document_page(image_path, document_name, document_processor, save_crops=save_crops)
            results.append(result)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\n{'='*60}")
        print(f"📊 PDF PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"   Total pages: {len(results)}")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📸 Images: payment_slip_{start_number}.jpg to payment_slip_{start_number + len(results) - 1}.jpg")
        print(f"{'='*60}")
        
        return {
            'type': 'pdf',
            'total': len(results),
            'successful': successful,
            'failed': failed,
            'start_number': start_number,
            'end_number': start_number + len(results) - 1,
            'results': results
        }
    
    else:
        return {'type': 'unknown', 'error': f'Unsupported file type: {file_ext}'}