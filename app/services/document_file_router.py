# app/services/document_file_router.py

from pathlib import Path
from datetime import datetime
from app.db.document_repository import (
    get_last_cheque_id, get_last_deposit_id, get_last_receipt_id,
    get_next_cheque_name, get_next_deposit_name, get_next_receipt_name,
    create_slip_placeholder, create_deposit_placeholder, create_receipt_placeholder,
    update_slip_document, update_deposit_document, update_receipt_document,
    update_document_status
)
from app.db.document_storage_repository import save_processed_image
from app.services.document_pdf_service import pdf_to_document_images_continue


def process_single_document_page(image_path, image_name, document_processor, save_crops=False, save_image=True):
    """
    Process a single document image page - EXTRACTION ONLY.
    
    Args:
        image_path: Path to the image file
        image_name: Name for logging
        document_processor: DocumentProcessor instance
        save_crops: Whether to save cropped fields
        save_image: If False, don't save the image (let API router handle it)
    """
    print(f"\n{'='*50}")
    print(f"📄 Processing: {image_name}")
    print(f"{'='*50}")
    
    # Process the document (extraction only - NO INSERT)
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
    # IMPORTANT: This is just a suggestion, the API router will override it with sequential IDs
    if document_type == 'bank_cheque':
        suggested_name = get_next_cheque_name()
        print(f"📸 Suggested name: {suggested_name}")
    elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
        suggested_name = get_next_deposit_name()
        print(f"📸 Suggested name: {suggested_name}")
    else:
        suggested_name = get_next_receipt_name()
        print(f"📸 Suggested name: {suggested_name}")
    
    # Optionally save the image (disabled by default for PDF batch processing)
    image_filename = None
    if save_image:
        save_result = save_processed_image(image_path, suggested_name)
        
        if not save_result['success']:
            print(f"   ⚠️ Failed to save image: {save_result['error']}")
            image_filename = suggested_name
        else:
            image_filename = save_result['filename']
            print(f"   ✅ Image saved as: {image_filename}")
    else:
        print(f"   ℹ️ Image saving disabled (will be saved by API router)")
        image_filename = suggested_name
    
    # Return extraction results ONLY - NO DATABASE INSERT HERE
    return {
        'success': True,
        'document_type': document_type,
        'extracted_data': extracted_data,
        'image_name': image_filename,
        'suggested_name': suggested_name,
        'full_text': full_text,
        'image_path': image_path  # Return the path so API router can save it
    }


def process_document_file(file_path, filename, processor, save_crops=False, save_images=False):
    """
    Process document file (PDF or image)
    
    Args:
        file_path: Path to the file
        filename: Original filename
        processor: DocumentProcessor instance
        save_crops: Whether to save cropped field images
        save_images: If False, don't save images (let API router handle it)
    """
    file_ext = Path(filename).suffix.lower()

    print(f"\n{'='*60}")
    print(f"🔍 [DEBUG] process_document_file called")
    print(f"   file_path: {file_path}")
    print(f"   filename: {filename}")
    print(f"   file_ext: {file_ext}")
    print(f"   save_images: {save_images}")
    print(f"{'='*60}")
    
    # CASE 1: Single Image File
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print("🖼️ Detected: Single Image File")
        print(f"   File: {filename}")
        
        temp_name = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        result = process_single_document_page(
            file_path, temp_name, processor, 
            save_crops=save_crops, 
            save_image=save_images  # Pass the flag
        )
        
        return {
            'type': 'image',
            'total': 1,
            'successful': 1 if result['success'] else 0,
            'failed': 0 if result['success'] else 1,
            'results': [result]
        }
    
    # CASE 2: PDF File - Return extraction results ONLY (no placeholder)
    elif file_ext == '.pdf':
        print("="*60)
        print("📚 PDF FILE DETECTED")
        print("="*60)
        print(f"   File: {filename}")
        
        print(f"\n🔄 Converting PDF to images...")
        image_paths = pdf_to_document_images_continue(file_path, start_from=1)
        
        if not image_paths:
            print(f"❌ PDF CONVERSION FAILED!")
            return {
                'type': 'pdf', 
                'total': 0, 
                'successful': 0, 
                'failed': 0, 
                'error': 'PDF conversion failed - no pages extracted'
            }
        
        total_pages = len(image_paths)
        print(f"\n✅ PDF CONVERSION SUCCESSFUL!")
        print(f"   Total pages converted: {total_pages}")
        
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
            
            temp_name = f"temp_page_{idx}.jpg"
            
            # Process each page - returns extraction results ONLY
            # For PDFs, don't save images here - let API router handle it with sequential IDs
            result = process_single_document_page(
                image_path, temp_name, processor, 
                save_crops=save_crops, 
                save_image=save_images  # Usually False for PDFs
            )
            
            # Add the original temp image path to the result
            result['temp_image_path'] = image_path
            
            results.append(result)
            
            if result['success']:
                successful_count += 1
                print(f"\n   ✅ Page {idx} processed successfully!")
                print(f"      Type: {result['document_type']}")
                print(f"      Extracted data preview: {str(result['extracted_data'])[:100]}...")
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
        if total_pages > 0:
            print(f"   📈 Success rate: {(successful_count/total_pages)*100:.1f}%")
        print(f"{'='*60}")
        
        # Return results WITHOUT database operations
        # The API route will create placeholders for each result and save images
        return {
            'type': 'pdf',
            'total': total_pages,
            'successful': successful_count,
            'failed': failed_count,
            'results': results,
            'temp_images': image_paths  # Also return the list of temp images
        }
    
    else:
        print(f"❌ UNSUPPORTED FILE TYPE: {file_ext}")
        print(f"   Allowed types: .jpg, .jpeg, .png, .bmp, .tiff, .pdf")
        return {
            'type': 'unknown', 
            'error': f'Unsupported file type: {file_ext}'
        }