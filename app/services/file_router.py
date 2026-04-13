"""File router for handling both images and PDFs."""

from pathlib import Path
from app.db.invoice_repository import get_last_invoice_id, get_next_image_name
from app.services.pdf_service import pdf_to_images_continue
from app.services.invoice_processor import process_single_invoice


def process_invoice_file(file_path, filename, extractor, qwen_parser):
    """Main entry point - handles both single images and PDFs."""
    file_ext = Path(filename).suffix.lower()
    
    # CASE 1: Single Image File
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        print("🖼️ Detected: Single Image File")
        
        image_name = get_next_image_name()
        print(f"📸 Assigned image name: {image_name}")
        
        result = process_single_invoice(file_path, image_name, extractor, qwen_parser)
        
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
        
        last_id = get_last_invoice_id()
        start_number = last_id + 1
        
        print(f"\n📊 Database Status:")
        print(f"   Last invoice ID: {last_id}")
        print(f"   Starting from: inv_{start_number}.jpg")
        
        print(f"\n🔄 Converting PDF to images...")
        image_paths = pdf_to_images_continue(file_path, start_from=start_number)
        
        if not image_paths:
            return {'type': 'pdf', 'total': 0, 'successful': 0, 'failed': 0, 'error': 'PDF conversion failed'}
        
        results = []
        for idx, image_path in enumerate(image_paths):
            current_number = start_number + idx
            image_name = f"inv_{current_number}.jpg"
            
            print(f"\n📄 Processing page {idx+1}/{len(image_paths)}: {image_name}")
            
            result = process_single_invoice(image_path, image_name, extractor, qwen_parser)
            results.append(result)
        
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\n{'='*60}")
        print(f"📊 PDF PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"   Total pages: {len(results)}")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📸 Images: inv_{start_number}.jpg to inv_{start_number + len(results) - 1}.jpg")
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