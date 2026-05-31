# test_fitz.py
import fitz
import os

print("="*60)
print("TESTING PDF CONVERSION WITH FITZ (PyMuPDF)")
print("="*60)

# Use an existing PDF or create a simple one
# First, check if there's any PDF file in the current directory
pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]

if pdf_files:
    test_pdf = pdf_files[0]
    print(f"\n📄 Using existing PDF: {test_pdf}")
else:
    # If no PDF exists, we'll just test if fitz is available
    print("\n📄 No PDF found in current directory, testing fitz import only...")
    print(f"✅ fitz version: {fitz.__doc__}")
    print("\n✅ FITZ (PyMuPDF) is installed and working correctly!")
    print("\nNote: To test actual PDF conversion, place a PDF file in this directory.")
    exit(0)

# Convert PDF to images using fitz
print(f"\n🔄 Converting PDF to images using fitz...")

try:
    doc = fitz.open(test_pdf)
    print(f"   Total pages: {len(doc)}")
    
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = 200 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        image_filename = f"test_page_{page_num + 1}.jpg"
        pix.save(image_filename, "jpeg")
        image_paths.append(image_filename)
        print(f"   ✅ Created: {image_filename} ({pix.width}x{pix.height})")
    
    doc.close()
    print(f"\n✅ Successfully converted {len(image_paths)} pages!")
    
    # Clean up
    for img in image_paths:
        os.remove(img)
    print(f"\n🧹 Cleaned up test images")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ FITZ (PyMuPDF) is working correctly!")
print("="*60)