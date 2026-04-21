"""PDF conversion service."""

import os
import tempfile
import fitz


def pdf_to_images_continue(pdf_path, start_from=1, output_folder=None):
    """Convert PDF to images continuing from a specific number."""
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found - {pdf_path}")
        return []
    
    if output_folder is None:
        output_folder = tempfile.mkdtemp(prefix='pdf_pages_')
    else:
        os.makedirs(output_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    image_paths = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = 200 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        image_number = start_from + page_num
        image_filename = f"temp_page_{image_number}.jpg"
        image_path = os.path.join(output_folder, image_filename)
        
        pix.save(image_path)
        image_paths.append(image_path)
        # REMOVED: print(f"   ✅ Created: {image_filename}")
    
    doc.close()
    # REMOVED: print(f"\n📸 Converted {len(image_paths)} pages...")
    
    return image_paths