# app/services/document_pdf_service.py

import os
import tempfile
import fitz  # PyMuPDF


def pdf_to_document_images_continue(pdf_path, start_from=1, output_folder=None):
    """Convert PDF to images continuing from a specific number for documents."""
    print(f"\n{'='*60}")
    print(f"🔍 [DEBUG] pdf_to_document_images_continue CALLED!")
    print(f"   pdf_path: {pdf_path}")
    print(f"   start_from: {start_from}")
    print(f"{'='*60}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found - {pdf_path}")
        return []
    
    # Get file size
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"   File size: {file_size:.2f} MB")
    
    if output_folder is None:
        output_folder = tempfile.mkdtemp(prefix='document_pages_')
        print(f"   Temp folder: {output_folder}")
    else:
        os.makedirs(output_folder, exist_ok=True)
        print(f"   Output folder: {output_folder}")
    
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"   Total pages in PDF: {total_pages}")
        
        image_paths = []
        
        for page_num in range(total_pages):
            page = doc[page_num]
            print(f"\n   📄 Converting page {page_num + 1}/{total_pages}...")
            
            # Convert to image with 200 DPI
            zoom = 200 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            image_number = start_from + page_num
            image_filename = f"doc_{image_number}.jpg"
            image_path = os.path.join(output_folder, image_filename)
            
            pix.save(image_path, "jpeg")
            image_paths.append(image_path)
            
            # Get image size
            img_size = os.path.getsize(image_path) / 1024
            print(f"      ✅ Created: {image_filename} ({img_size:.1f} KB, {pix.width}x{pix.height})")
        
        doc.close()
        
        print(f"\n📸 PDF CONVERSION COMPLETE:")
        print(f"   Total images created: {len(image_paths)}")
        print(f"   First image: {image_paths[0] if image_paths else 'None'}")
        print(f"   Last image: {image_paths[-1] if image_paths else 'None'}")
        
        return image_paths
        
    except Exception as e:
        print(f"❌ Error converting PDF: {e}")
        import traceback
        traceback.print_exc()
        return []