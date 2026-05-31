# app/services/document_processor_service.py

import os
import tempfile
from pathlib import Path
from datetime import datetime
from app.services.document_processor import DocumentProcessor, clean_amount_value
from app.db.document_repository import (
    get_last_document_id, 
    get_next_document_name,
    get_next_cheque_name,
    get_next_deposit_name,
    get_next_receipt_name
)
from app.db.document_storage_repository import save_processed_image


def process_single_document_page(image_path, temp_name, document_processor, save_crops=False):
    """
    Process a single document image page - EXTRACTION ONLY, NO DATABASE INSERT.
    Returns extracted data and generated permanent filename.
    """
    print(f"\n{'='*50}")
    print(f"📄 Processing: {temp_name}")
    print(f"{'='*50}")
    
    # Process the document (extraction only)
    result = document_processor.process_document(image_path, save_crops=save_crops)
    
    if not result.get('success'):
        return {
            'success': False, 
            'error': result.get('error', 'Processing failed'), 
            'temp_name': temp_name
        }
    
    extracted_data = result.get('extracted_data', {})
    document_type = result.get('document_type', 'unknown')
    full_text = result.get('full_text', '')
    
    print(f"\n📋 Document Type: {document_type}")
    print(f"📋 Extracted data: {extracted_data}")
    
    # Generate permanent image name based on document type
    if document_type == 'bank_cheque':
        permanent_name = get_next_cheque_name()
        print(f"   💾 This will be saved as: {permanent_name}")
    elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
        permanent_name = get_next_deposit_name()
        print(f"   💾 This will be saved as: {permanent_name}")
    else:
        permanent_name = get_next_receipt_name()
        print(f"   💾 This will be saved as: {permanent_name}")
    
    # Save the processed image with permanent name
    save_result = save_processed_image(image_path, permanent_name)
    
    if not save_result['success']:
        print(f"   ⚠️ Failed to save image: {save_result['error']}")
        image_filename = permanent_name
    else:
        image_filename = save_result['filename']
        print(f"   ✅ Image saved as: {image_filename}")
    
    # Return extraction results (NO DATABASE INSERT HERE)
    return {
        'success': True,
        'document_type': document_type,
        'extracted_data': extracted_data,
        'image_name': image_filename,
        'full_text': full_text,
        'permanent_name': permanent_name
    }


def process_document_file(file_path, filename, document_processor, save_crops=False):
    """
    Main entry point - handles both single images and PDFs for documents.
    RETURNS EXTRACTION RESULTS ONLY, NO DATABASE OPERATIONS.
    """
    file_ext = Path(filename).suffix.lower()
    
    # CASE 1: Single Image File
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print("🖼️ Detected: Single Image File")
        print(f"   File: {filename}")
        
        temp_name = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        result = process_single_document_page(file_path, temp_name, document_processor, save_crops=save_crops)
        
        return {
            'type': 'image',
            'total': 1,
            'successful': 1 if result['success'] else 0,
            'failed': 0 if result['success'] else 1,
            'results': [result]
        }
    
    # CASE 2: PDF File
    elif file_ext == '.pdf':
        print("="*60)
        print("📚 PDF FILE DETECTED")
        print("="*60)
        print(f"   File: {filename}")
        
        from app.services.document_pdf_service import pdf_to_document_images_continue
        
        print(f"\n🔄 Converting PDF to images...")
        print(f"   Source: {file_path}")
        
        # Convert PDF to images
        image_paths = pdf_to_document_images_continue(file_path, start_from=1)
        
        if not image_paths:
            print(f"\n❌ PDF CONVERSION FAILED!")
            print(f"   No images were extracted from the PDF.")
            return {'type': 'pdf', 'total': 0, 'successful': 0, 'failed': 0, 'error': 'PDF conversion failed'}
        
        total_pages = len(image_paths)
        print(f"\n✅ PDF CONVERSION SUCCESSFUL!")
        print(f"   Total pages converted: {total_pages}")
        print(f"   Image paths:")
        for idx, img_path in enumerate(image_paths, 1):
            print(f"      Page {idx}: {img_path}")
        
        print(f"\n{'='*60}")
        print(f"📄 PROCESSING PDF PAGES")
        print(f"{'='*60}")
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for idx, image_path in enumerate(image_paths, 1):
            print(f"\n{'─'*50}")
            print(f"📄 PROCESSING PAGE {idx} OF {total_pages}")
            print(f"{'─'*50}")
            print(f"   Image path: {image_path}")
            print(f"   Page size: {os.path.getsize(image_path)} bytes")
            
            temp_name = f"temp_page_{idx}.jpg"
            
            result = process_single_document_page(image_path, temp_name, document_processor, save_crops=save_crops)
            results.append(result)
            
            if result['success']:
                successful_count += 1
                print(f"\n   ✅ Page {idx} processed successfully!")
                print(f"      Document Type: {result['document_type']}")
                print(f"      Saved as: {result['image_name']}")
            else:
                failed_count += 1
                print(f"\n   ❌ Page {idx} processing failed!")
                print(f"      Error: {result.get('error', 'Unknown error')}")
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"📊 PDF PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"   📄 Total pages in PDF: {total_pages}")
        print(f"   ✅ Successfully processed: {successful_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   📈 Success rate: {(successful_count/total_pages)*100:.1f}%")
        print(f"{'='*60}")
        
        # Print list of successfully processed pages
        if successful_count > 0:
            print(f"\n📸 SUCCESSFULLY PROCESSED PAGES:")
            for idx, result in enumerate(results, 1):
                if result['success']:
                    print(f"   Page {idx}: {result['image_name']} ({result['document_type']})")
        
        return {
            'type': 'pdf',
            'total': total_pages,
            'successful': successful_count,
            'failed': failed_count,
            'results': results
        }
    
    else:
        print(f"❌ UNSUPPORTED FILE TYPE: {file_ext}")
        print(f"   Allowed types: .jpg, .jpeg, .png, .bmp, .tiff, .pdf")
        return {'type': 'unknown', 'error': f'Unsupported file type: {file_ext}'}