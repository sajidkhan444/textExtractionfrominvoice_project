"""FastAPI routes for invoice processing."""

import os
import tempfile
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from app.api.schemas import (
    UploadResponse, SearchResponse, InvoiceInfo, HealthResponse,
    ExternalInvoiceResponse
)
from app.dependencies import extractor, qwen_parser
from app.services.invoice_processor import process_single_invoice, process_external_invoice
from app.services.pdf_service import pdf_to_images_continue
from app.db.invoice_repository import (
    get_all_invoices, get_invoice_by_id, count_invoices, 
    search_invoices, get_last_invoice_id, get_next_image_name,
    get_last_completed_invoice_id, create_external_placeholder,
    update_invoice_status
)
from app.db.storage_repository import list_all_images
from app.config import PROCESSED_INVOICES_PATH, TEMP_DIR  # NEW
from datetime import datetime

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_status = "healthy"
    try:
        count_invoices()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    storage_status = "healthy"
    try:
        if not os.path.exists(PROCESSED_INVOICES_PATH):
            storage_status = "unhealthy: path not found"
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="ok",
        database=db_status,
        storage=storage_status,
        version="1.0.0"
    )


# FIRST API ENDPOINT FOR ONLY TESTING
@router.post("/ocr-text-extraction", response_model=UploadResponse, tags=["ocr-text-extraction"])
async def upload_invoice(file: UploadFile = File(...)):
    """
    Upload a single invoice image or PDF.
    
    - **file**: Image file (JPG, PNG, JPEG, BMP, TIFF) or PDF file
    - Single image: Processed directly, returns single invoice result
    - PDF: All pages extracted and processed sequentially, returns batch result
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # =====================================================
        # CASE 1: PDF FILE - Process all pages
        # =====================================================
        if file_ext == '.pdf':
            last_id = get_last_invoice_id()
            start_number = last_id + 1
            
            print(f"\n📚 PDF Detected: {file.filename}")
            print(f"   Last invoice ID: {last_id}")
            print(f"   Starting from: inv_{start_number}.jpg")
            
            # Convert PDF to images
            image_paths = pdf_to_images_continue(tmp_path, start_from=start_number)
            
            if not image_paths:
                return UploadResponse(
                    success=False,
                    type="pdf",
                    message="PDF conversion failed",
                    error="Could not convert PDF to images"
                )
            
            print(f"   Converted {len(image_paths)} pages")
            
            # Process each page
            invoices = []
            successful_count = 0
            failed_count = 0
            
            for idx, img_path in enumerate(image_paths):
                current_number = start_number + idx
                image_name = f"inv_{current_number}.jpg"
                
                print(f"\n   📄 Processing page {idx+1}/{len(image_paths)}: {image_name}")
                
                result = process_single_invoice(img_path, image_name, extractor, qwen_parser)
                
                if result['success']:
                    successful_count += 1
                    invoices.append({
                        "invoice_id": result['invoice_id'],
                        "image_name": result['image_name'],
                        "company_name": result['clean_data'].get('company_name'),
                        "phone_number": result['clean_data'].get('phone_number'),
                        "strn": result['clean_data'].get('strn'),
                        "ntn": result['clean_data'].get('ntn'),
                        "order_number": result['clean_data'].get('order_number'),
                        "invoice_number": result['clean_data'].get('invoice_number'),
                        "date": result['clean_data'].get('date')
                    })
                    print(f"      ✅ Success (ID: {result['invoice_id']})")
                else:
                    failed_count += 1
                    invoices.append({
                        "success": False,
                        "image_name": image_name,
                        "error": result.get('error', 'Unknown error')
                    })
                    print(f"      ❌ Failed: {result.get('error')}")
            
            print(f"\n   📊 PDF Processing Complete:")
            print(f"      Total pages: {len(image_paths)}")
            print(f"      Successful: {successful_count}")
            print(f"      Failed: {failed_count}")
            
            return UploadResponse(
                success=successful_count > 0,
                type="pdf",
                message=f"Processed {len(image_paths)} pages, {successful_count} successful",
                total_pages=len(image_paths),
                successful_pages=successful_count,
                failed_pages=failed_count,
                start_number=start_number,
                end_number=start_number + len(image_paths) - 1,
                invoices=invoices,
                error=None if successful_count > 0 else "All pages failed"
            )
        
        # =====================================================
        # CASE 2: SINGLE IMAGE - Process directly
        # =====================================================
        else:
            image_name = get_next_image_name()
            
            print(f"\n🖼️ Image Detected: {file.filename}")
            print(f"   Assigned name: {image_name}")
            
            result = process_single_invoice(tmp_path, image_name, extractor, qwen_parser)
            
            if result['success']:
                return UploadResponse(
                    success=True,
                    type="image",
                    message="Invoice processed successfully",
                    invoice_id=result['invoice_id'],
                    image_name=result['image_name'],
                    extracted_data=result['clean_data'],
                    error=None
                )
            else:
                return UploadResponse(
                    success=False,
                    type="image",
                    message="Invoice processing failed",
                    error=result.get('error', 'Unknown error')
                )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# SECOND API ENDPOINT FOR EXTERNAL REQUEST HANDLER
@router.post("/external-invoice", response_model=ExternalInvoiceResponse, tags=["External Department"])
async def external_invoice_upload(
    invoicename: str = Form(...),
    rack_no: str = Form(...),
    voucher: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(...)
):
    """
    ENDPOINT FOR OTHER DEPARTMENT - Production use only.
    
    Submits invoice with metadata from external department.
    Supports both single images and multi-page PDFs.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    temp_file_path = os.path.join(TEMP_DIR, f"external_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}")
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # =====================================================
        # CASE 1: PDF FILE - Process all pages
        # =====================================================
        if file_ext == '.pdf':
            # Get last completed invoice ID for filename generation
            last_completed_id = get_last_completed_invoice_id()
            
            # If no completed invoices exist, start from 1
            if last_completed_id == 0:
                start_number = 1
                print(f"\n📚 EXTERNAL PDF - FRESH DATABASE DETECTED")
            else:
                start_number = last_completed_id + 1
            
            print(f"\n📚 EXTERNAL PDF Detected: {file.filename}")
            print(f"   Last completed ID: {last_completed_id if last_completed_id > 0 else 'None'}")
            print(f"   Metadata: {invoicename}, {rack_no}, {voucher}, {date}")
            
            # Convert PDF to images
            image_paths = pdf_to_images_continue(temp_file_path, start_from=start_number)
            
            if not image_paths:
                return ExternalInvoiceResponse(
                    status="failed",
                    message="PDF conversion failed",
                    invoice_id=None
                )
            
            print(f"   📄 Total pages: {len(image_paths)}")
            print(f"   🔄 Starting sequential processing...")
            
            # Process each page
            successful_count = 0
            failed_count = 0
            first_invoice_id = None
            processed_filenames = []
            
            for idx, img_path in enumerate(image_paths):
                print(f"\n   📄 Processing page {idx+1}/{len(image_paths)}...")
                
                # Create placeholder for each page
                placeholder_result = create_external_placeholder(
                    invoicename=f"{invoicename}_page_{idx+1}",
                    rack_no=rack_no,
                    voucher=voucher,
                    date=date,
                    image_path=img_path
                )
                
                if not placeholder_result['success']:
                    failed_count += 1
                    print(f"      ❌ Failed to create placeholder")
                    continue
                
                invoice_id = placeholder_result['invoice_id']
                if first_invoice_id is None:
                    first_invoice_id = invoice_id
                
                # Process through AI pipeline (this will generate dynamic filename)
                result = process_external_invoice(
                    image_path=img_path,
                    image_name=f"temp_page_{idx+1}",
                    extractor=extractor,
                    qwen_parser=qwen_parser,
                    invoice_id=invoice_id,
                    invoicename=f"{invoicename}_page_{idx+1}"
                )
                
                if result['success']:
                    successful_count += 1
                    processed_filenames.append(result['image_name'])
                    print(f"      ✅ Saved as: {result['image_name']}")
                else:
                    failed_count += 1
                    print(f"      ❌ Failed: {result['error']}")
            
            print(f"\n   📊 EXTERNAL PDF Processing Complete:")
            print(f"      Total pages: {len(image_paths)}")
            print(f"      ✅ Successful: {successful_count}")
            print(f"      ❌ Failed: {failed_count}")
            
            if processed_filenames:
                print(f"      📸 Saved files:")
                for fname in processed_filenames:
                    print(f"         - {fname}")
            
            if successful_count > 0:
                return ExternalInvoiceResponse(
                    status="success",
                    message=f"Processed {successful_count}/{len(image_paths)} pages successfully",
                    invoice_id=first_invoice_id
                )
            else:
                return ExternalInvoiceResponse(
                    status="failed",
                    message="All pages failed to process",
                    invoice_id=None
                )
        
        # =====================================================
        # CASE 2: SINGLE IMAGE - Process directly
        # =====================================================
        else:
            # Get last completed invoice ID for filename generation
            last_completed_id = get_last_completed_invoice_id()
            
            # If no completed invoices exist, start from 1
            if last_completed_id == 0:
                next_id = 1
                image_name = f"inv_1.jpg"
                print(f"\n📥 EXTERNAL SINGLE IMAGE - FRESH DATABASE DETECTED")
                print(f"   Starting fresh")
            else:
                next_id = last_completed_id + 1
                image_name = f"temp_image_{next_id}.jpg"
            
            print(f"\n📥 EXTERNAL SINGLE IMAGE REQUEST:")
            print(f"   invoicename: {invoicename}")
            print(f"   rack_no: {rack_no}")
            print(f"   voucher: {voucher}")
            print(f"   date: {date}")
            print(f"   last_completed_id: {last_completed_id if last_completed_id > 0 else 'None'}")
            
            # Step 1: Create placeholder row with metadata
            placeholder_result = create_external_placeholder(
                invoicename=invoicename,
                rack_no=rack_no,
                voucher=voucher,
                date=date,
                image_path=temp_file_path
            )
            
            if not placeholder_result['success']:
                raise HTTPException(status_code=500, detail=f"Failed to create placeholder: {placeholder_result['error']}")
            
            invoice_id = placeholder_result['invoice_id']
            print(f"   ✅ External placeholder created with invoice_id: {invoice_id}")
            
            # Step 2: Process the image through AI pipeline
            result = process_external_invoice(
                image_path=temp_file_path,
                image_name=image_name,
                extractor=extractor,
                qwen_parser=qwen_parser,
                invoice_id=invoice_id,
                invoicename=invoicename
            )
            
            if not result['success']:
                print(f"   ❌ External processing failed: {result['error']}")
                return ExternalInvoiceResponse(
                    status="failed",
                    message=f"Processing failed: {result['error']}",
                    invoice_id=invoice_id
                )
            
            print(f"   ✅ External invoice {invoice_id} fully processed and updated!")
            print(f"   📸 Final filename: {result['image_name']}")
            
            return ExternalInvoiceResponse(
                status="success",
                message="Invoice processed and saved successfully",
                invoice_id=invoice_id
            )
        
    except Exception as e:
        print(f"❌ External endpoint error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)