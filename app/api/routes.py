"""FastAPI routes for invoice processing."""

import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.api.schemas import (
    UploadResponse, SearchResponse, InvoiceInfo, HealthResponse
)
from app.dependencies import extractor, qwen_parser
from app.services.invoice_processor import process_single_invoice
from app.services.pdf_service import pdf_to_images_continue
from app.db.invoice_repository import (
    get_all_invoices, get_invoice_by_id, count_invoices, 
    search_invoices, get_last_invoice_id, get_next_image_name
)
from app.db.storage_repository import list_all_images
from app.config import LOCAL_STORAGE_PATH

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
        if not os.path.exists(LOCAL_STORAGE_PATH):
            storage_status = "unhealthy: path not found"
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="ok",
        database=db_status,
        storage=storage_status,
        version="1.0.0"
    )


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


@router.get("/invoices", response_model=SearchResponse, tags=["Database"])
async def get_invoices(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all invoices with pagination."""
    result = get_all_invoices(limit=limit, offset=offset)
    
    if result['success']:
        invoices = []
        for inv in result['invoices']:
            invoices.append(InvoiceInfo(
                invoice_id=inv['invoice_id'],
                company_name=inv.get('company_name'),
                phone_number=inv.get('phone_number'),
                strn=inv.get('strn'),
                ntn=inv.get('ntn'),
                order_number=inv.get('order_number'),
                invoice_number=inv.get('invoice_number'),
                invoice_date=str(inv.get('invoice_date')) if inv.get('invoice_date') else None,
                invoice_image_path=inv.get('invoice_image_path'),
                created_at=inv.get('created_at')
            ))
        
        return SearchResponse(
            success=True,
            count=len(invoices),
            results=invoices
        )
    else:
        return SearchResponse(
            success=False,
            count=0,
            results=[]
        )


@router.get("/invoices/{invoice_id}", response_model=InvoiceInfo, tags=["Database"])
async def get_invoice(invoice_id: int):
    """Get invoice by ID."""
    result = get_invoice_by_id(invoice_id)
    
    if result['success']:
        inv = result['invoice']
        return InvoiceInfo(
            invoice_id=inv['invoice_id'],
            company_name=inv.get('company_name'),
            phone_number=inv.get('phone_number'),
            strn=inv.get('strn'),
            ntn=inv.get('ntn'),
            order_number=inv.get('order_number'),
            invoice_number=inv.get('invoice_number'),
            invoice_date=str(inv.get('invoice_date')) if inv.get('invoice_date') else None,
            invoice_image_path=inv.get('invoice_image_path'),
            created_at=inv.get('created_at')
        )
    else:
        raise HTTPException(status_code=404, detail="Invoice not found")


@router.get("/search", response_model=SearchResponse, tags=["Database"])
async def search(query: str = Query(..., min_length=1)):
    """Search invoices by company name, NTN, or invoice number."""
    result = search_invoices(query)
    
    if result['success']:
        invoices = []
        for inv in result['results']:
            invoices.append(InvoiceInfo(
                invoice_id=inv['invoice_id'],
                company_name=inv.get('company_name'),
                phone_number=inv.get('phone_number'),
                strn=inv.get('strn'),
                ntn=inv.get('ntn'),
                order_number=inv.get('order_number'),
                invoice_number=inv.get('invoice_number'),
                invoice_date=str(inv.get('invoice_date')) if inv.get('invoice_date') else None,
                invoice_image_path=inv.get('invoice_image_path'),
                created_at=inv.get('created_at')
            ))
        
        return SearchResponse(
            success=True,
            count=len(invoices),
            results=invoices
        )
    else:
        return SearchResponse(
            success=False,
            count=0,
            results=[]
        )


@router.get("/stats", tags=["Database"])
async def get_stats():
    """Get database statistics."""
    count_result = count_invoices()
    last_id = get_last_invoice_id()
    next_name = get_next_image_name()
    storage_result = list_all_images()
    
    return {
        "total_invoices": count_result.get('count', 0) if count_result['success'] else 0,
        "last_invoice_id": last_id,
        "next_image_name": next_name,
        "total_images_in_storage": len(storage_result.get('images', [])) if storage_result['success'] else 0,
        "storage_path": LOCAL_STORAGE_PATH
    }