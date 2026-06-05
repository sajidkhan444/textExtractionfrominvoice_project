# app/api/document_routes.py

import os
import shutil
import json
import tempfile
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
from pydantic import BaseModel

from app.services.document_file_router import process_document_file
from app.services.document_processor import DocumentProcessor
from app.services.document_pdf_service import pdf_to_document_images_continue
from app.db.document_repository import (
    get_last_document_id, 
    get_all_documents, 
    get_document_by_id, 
    count_documents, 
    search_documents,
    create_slip_placeholder, 
    create_deposit_placeholder, 
    create_receipt_placeholder,
    update_slip_document, 
    update_deposit_document, 
    update_receipt_document,
    update_document_status, 
    get_current_max_id
)
from app.config import DOCUMENT_STORAGE_PATH
from app.core.documents_config import DocumentsConfig

# Initialize router
router = APIRouter(tags=["Document Processing"])

# Initialize processor (singleton)
_processor = None

def get_processor():
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor


# ============================================
# PRODUCTION API 1: BANK CHEQUE (PAYMENT SLIP)
# ============================================

@router.post("/api/documents/upload/cheque")
async def upload_cheque_document(
    cheque_image: UploadFile = File(..., description="Cheque image or PDF file"),
    slip_name: str = Form(..., description="Document name for bank cheque"),
    rack_no: str = Form(..., description="Rack number"),
    voucher_number: str = Form(..., description="Voucher number"),
    background_tasks: BackgroundTasks = None
):
    """
    PRODUCTION API - Upload Bank Cheque (Payment Slip)
    
    Payload:
    - slip_name: Document name (required)
    - rack_no: Rack number (required)
    - voucher_number: Voucher number (required)
    - cheque_image: Image or PDF file (required)
    """
    return await process_document_upload(
        file=cheque_image,
        doc_name=slip_name,
        rack_no=rack_no,
        voucher_number=voucher_number,
        expected_doc_type="bank_cheque"
    )


# ============================================
# PRODUCTION API 2: DEPOSIT SLIP
# ============================================

@router.post("/api/documents/upload/deposit")
async def upload_deposit_document(
    deposit_image: UploadFile = File(..., description="Deposit slip image or PDF file"),
    deposit_name: str = Form(..., description="Document name for deposit slip"),
    rack_no: str = Form(..., description="Rack number"),
    voucher_number: str = Form(..., description="Voucher number"),
    background_tasks: BackgroundTasks = None
):
    """
    PRODUCTION API - Upload Deposit Slip
    
    Payload:
    - deposit_name: Document name (required)
    - rack_no: Rack number (required)
    - voucher_number: Voucher number (required)
    - deposit_image: Image or PDF file (required)
    """
    return await process_document_upload(
        file=deposit_image,
        doc_name=deposit_name,
        rack_no=rack_no,
        voucher_number=voucher_number,
        expected_doc_type="bank_deposit_slips"
    )


# ============================================
# PRODUCTION API 3: DIGITAL RECEIPT
# ============================================

@router.post("/api/documents/upload/receipt")
async def upload_receipt_document(
    digital_image: UploadFile = File(..., description="Digital receipt image or PDF file"),
    receipt_name: str = Form(..., description="Document name for digital receipt"),
    rack_no: str = Form(..., description="Rack number"),
    voucher_number: str = Form(..., description="Voucher number"),
    background_tasks: BackgroundTasks = None
):
    """
    PRODUCTION API - Upload Digital Receipt
    
    Payload:
    - receipt_name: Document name (required)
    - rack_no: Rack number (required)
    - voucher_number: Voucher number (required)
    - digital_image: Image or PDF file (required)
    """
    return await process_document_upload(
        file=digital_image,
        doc_name=receipt_name,
        rack_no=rack_no,
        voucher_number=voucher_number,
        expected_doc_type="digital_bank_receipt"
    )


# ============================================
# HELPER FUNCTION: Get unique filename for PDF page
# ============================================

def get_unique_filename_for_page(document_type: str, page_num: int, current_max_id: int) -> tuple:
    """
    Generate unique sequential filename for a PDF page.
    
    Args:
        document_type: Type of document (bank_cheque, bank_deposit_slips, digital_bank_receipt)
        page_num: Page number (for logging only)
        current_max_id: Current MAX ID from database BEFORE this page
    
    Returns:
        Tuple of (filename, new_id)
    """
    new_id = current_max_id + 1
    
    if document_type == "bank_cheque":
        return f"cheque_{new_id}.jpg", new_id
    elif document_type == "bank_deposit_slips":
        return f"deposit_{new_id}.jpg", new_id
    else:
        return f"receipt_{new_id}.jpg", new_id


# ============================================
# COMMON PROCESSING FUNCTION (FIXED WITH IMAGE SAVING)
# ============================================

async def process_document_upload(
    file: UploadFile,
    doc_name: str,
    rack_no: str,
    voucher_number: str,
    expected_doc_type: str
):
    """
    Common function to process document uploads for all three APIs.
    
    FIXED: Each PDF page now gets a UNIQUE sequential filename AND the image is saved.
    """
    print(f"\n{'='*70}")
    print(f"🔍 [API] Document Upload Started")
    print(f"   File: {file.filename}")
    print(f"   Document Name: {doc_name}")
    print(f"   Rack No: {rack_no}")
    print(f"   Voucher No: {voucher_number}")
    print(f"   Expected Type: {expected_doc_type}")
    print(f"{'='*70}")
    
    # Create temp folders for crops
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    crop_session_folder = os.path.join(DocumentsConfig.CROPPED_FOLDER, session_id)
    os.makedirs(crop_session_folder, exist_ok=True)
    original_cropped_folder = DocumentsConfig.CROPPED_FOLDER
    
    tmp_path = None
    temp_images_for_pdf = None  # Store temp images for PDF processing
    
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file temporarily
        print(f"   Saving temp file...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        print(f"   Temp file: {tmp_path}")
        print(f"   Size: {os.path.getsize(tmp_path)} bytes")
        
        # ============================================
        # Convert PDF to image FIRST for classification
        # ============================================
        processor = DocumentProcessor()
        
        if file_ext == '.pdf':
            print(f"\n📄 PDF detected - converting first page for classification...")
            temp_images_for_pdf = pdf_to_document_images_continue(tmp_path, start_from=1)
            if not temp_images_for_pdf:
                raise HTTPException(status_code=500, detail="Failed to convert PDF first page")
            classification_path = temp_images_for_pdf[0]
            print(f"   Using converted image for classification: {classification_path}")
        else:
            classification_path = tmp_path
        
        # Step 1: Classify document using image
        print(f"\n   Classifying document...")
        doc_type, confidence = processor.classify_document(classification_path)
        
        print(f"\n📋 CLASSIFICATION RESULT:")
        print(f"   Type: {doc_type}")
        print(f"   Confidence: {confidence:.2%}")
        
        # Validate document type matches expected
        is_cheque = doc_type == "bank_cheque"
        is_deposit = doc_type == "bank_deposit_slips"
        is_receipt = doc_type == "digital_bank_receipt"
        
        if expected_doc_type == "bank_cheque" and not is_cheque:
            raise HTTPException(
                status_code=400,
                detail=f"Document type mismatch. Expected bank cheque, but found {doc_type}"
            )
        elif expected_doc_type == "bank_deposit_slips" and not is_deposit:
            raise HTTPException(
                status_code=400,
                detail=f"Document type mismatch. Expected deposit slip, but found {doc_type}"
            )
        elif expected_doc_type == "digital_bank_receipt" and not is_receipt:
            raise HTTPException(
                status_code=400,
                detail=f"Document type mismatch. Expected digital receipt, but found {doc_type}"
            )
        
        # Clean up temp classification image
        if file_ext == '.pdf' and os.path.exists(classification_path):
            try:
                os.remove(classification_path)
            except:
                pass
        
        # Step 2: Process the document (extraction only - no image saving)
        print(f"\n🔄 Processing document...")
        # IMPORTANT: Pass save_images=False to prevent premature saving
        result = process_document_file(tmp_path, file.filename, processor, save_images=False)
        
        print(f"\n📊 Processing Result:")
        print(f"   Type: {result['type']}")
        if result['type'] == 'image':
            print(f"   Success: {result['results'][0]['success']}")
        else:
            print(f"   Total Pages: {result.get('total', 0)}")
            print(f"   Successful: {result.get('successful', 0)}")
            print(f"   Failed: {result.get('failed', 0)}")
        
        # Output directory for permanent storage
        output_dir = "C:\\Users\\Dell\\textExtractionfrominvoice_project\\data\\output\\documents"
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 3: Handle based on type
        if result['type'] == 'image' and result['results'][0]['success']:
            # SINGLE IMAGE - Create placeholder and update
            r = result['results'][0]
            extracted_data = r.get('extracted_data', {})
            suggested_filename = r.get('suggested_name', r.get('image_name'))
            document_type = r.get('document_type')
            
            # Get the temp image path
            temp_image_path = r.get('temp_image_path', tmp_path)
            
            # Get current max ID for single image
            current_max_result = get_current_max_id()
            if current_max_result['success']:
                current_max_id = current_max_result['max_id']
                new_id = current_max_id + 1
            else:
                new_id = 1
            
            # Generate unique filename
            if document_type == 'bank_cheque':
                image_filename = f"cheque_{new_id}.jpg"
            elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
                image_filename = f"deposit_{new_id}.jpg"
            else:
                image_filename = f"receipt_{new_id}.jpg"
            
            # ✅ SAVE THE IMAGE
            output_path = os.path.join(output_dir, image_filename)
            if os.path.exists(temp_image_path):
                shutil.copy2(temp_image_path, output_path)
                print(f"   ✅ Image saved permanently: {image_filename}")
                print(f"   📁 File size: {os.path.getsize(output_path)} bytes")
            else:
                print(f"   ⚠️ Warning: Temp image not found at {temp_image_path}")
            
            # Create placeholder
            if is_cheque:
                placeholder_result = create_slip_placeholder(doc_name, rack_no, voucher_number, file.filename)
                table_name = "slip"
            elif is_deposit:
                placeholder_result = create_deposit_placeholder(doc_name, rack_no, voucher_number, file.filename)
                table_name = "deposit"
            else:
                placeholder_result = create_receipt_placeholder(doc_name, rack_no, voucher_number, file.filename)
                table_name = "receipt"
            
            if not placeholder_result['success']:
                raise HTTPException(status_code=500, detail=f"Failed to create placeholder: {placeholder_result['error']}")
            
            document_id = placeholder_result['id']
            print(f"✅ Placeholder ID: {document_id} (status: processing)")
            
            # Update placeholder with extracted data
            if document_type == 'bank_cheque':
                update_result = update_slip_document(
                    slip_id=document_id,
                    bank_cheque_name=extracted_data.get('bank_name'),
                    account_holder_name=extracted_data.get('pay'),
                    cheque_number=extracted_data.get('check_number'),
                    iban=extracted_data.get('iban'),
                    cheque_amount=extracted_data.get('amount'),
                    cheque_image_filename=image_filename
                )
            elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
                update_result = update_deposit_document(
                    deposit_id=document_id,
                    bank_deposit_name=extracted_data.get('bank_name'),
                    account_title=extracted_data.get('account_title'),
                    account_number=extracted_data.get('account_number'),
                    depositor_name=extracted_data.get('depositor_name'),
                    contact_number=extracted_data.get('contact_number'),
                    cnic=extracted_data.get('cnic'),
                    deposit_amount=extracted_data.get('amount'),
                    deposit_image_filename=image_filename
                )
            else:
                update_result = update_receipt_document(
                    receipt_id=document_id,
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
            
            if not update_result['success']:
                update_document_status(document_id, table_name, 'failed')
                return {
                    "success": False,
                    "message": "Extraction succeeded but database update failed",
                    "error": update_result.get('error'),
                    "document_id": document_id
                }
            
            return {
                "success": True,
                "message": "Document processed successfully",
                "document_id": document_id,
                "image_name": image_filename,
                "document_type": document_type,
                "extracted_data": extracted_data,
                "metadata": {
                    "document_name": doc_name,
                    "rack_no": rack_no,
                    "voucher_number": voucher_number
                }
            }
        
        elif result['type'] == 'pdf' and result['successful'] > 0:
            # PDF BATCH PROCESSING - FIXED: Save images with unique filenames
            print(f"\n📄 Processing PDF with {result['total']} pages...")
            print(f"   ⚠️  Creating placeholders for ALL pages FIRST, then processing...")
            
            processed_documents = []
            
            # Output directory for permanent storage
            output_dir = "C:\\Users\\Dell\\textExtractionfrominvoice_project\\data\\output\\documents"
            os.makedirs(output_dir, exist_ok=True)
            
            # Get the list of temp images from the result
            temp_images = result.get('temp_images', [])
            if not temp_images:
                print(f"   ⚠️ No temp images in result, converting again...")
                temp_images = pdf_to_document_images_continue(tmp_path, start_from=1)
            
            # ============================================
            # STEP 1: Create placeholders for ALL pages FIRST
            # ============================================
            print(f"\n{'='*60}")
            print(f"📝 STEP 1: Creating placeholders for all {len(result['results'])} pages...")
            print(f"{'='*60}")
            
            # Get current max ID from database (across ALL tables)
            current_max_result = get_current_max_id()  
            if current_max_result['success']:
                current_max_id = current_max_result['max_id']
                print(f"   📍 Current MAX ID across all tables: {current_max_id}")
            else:
                current_max_id = 0
                print(f"   📍 Starting MAX ID: {current_max_id}")
            
            # Initialize page_placeholders list
            page_placeholders = []
            temp_max_id = current_max_id
            
            for idx, page_result in enumerate(result['results']):
                if not page_result['success']:
                    page_placeholders.append({
                        "success": False,
                        "error": page_result.get('error', 'Unknown error'),
                        "page": idx + 1
                    })
                    continue
                
                extracted_data = page_result.get('extracted_data', {})
                document_type = page_result.get('document_type')
                
                # Generate unique ID and filename for THIS page
                new_id = temp_max_id + 1
                
                if document_type == 'bank_cheque':
                    image_filename = f"cheque_{new_id}.jpg"
                    placeholder_result = create_slip_placeholder(f"{doc_name}_page_{idx + 1}", rack_no, voucher_number, file.filename)
                    table_name = "slip"
                elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
                    image_filename = f"deposit_{new_id}.jpg"
                    placeholder_result = create_deposit_placeholder(f"{doc_name}_page_{idx + 1}", rack_no, voucher_number, file.filename)
                    table_name = "deposit"
                else:
                    image_filename = f"receipt_{new_id}.jpg"
                    placeholder_result = create_receipt_placeholder(f"{doc_name}_page_{idx + 1}", rack_no, voucher_number, file.filename)
                    table_name = "receipt"
                
                print(f"\n   📄 Page {idx + 1}:")
                print(f"      Current MAX ID: {current_max_id}")
                print(f"      → New ID: {new_id}")
                print(f"      → Filename: {image_filename}")
                
                if not placeholder_result['success']:
                    page_placeholders.append({
                        "success": False,
                        "error": f"Failed to create placeholder: {placeholder_result['error']}",
                        "page": idx + 1
                    })
                    continue
                
                page_document_id = placeholder_result['id']
                print(f"      ✅ Placeholder created with ID: {page_document_id}")
                
                # Store placeholder info for later update
                page_placeholders.append({
                    "success": True,
                    "page": idx + 1,
                    "document_id": page_document_id,
                    "document_type": document_type,
                    "image_filename": image_filename,
                    "table_name": table_name,
                    "extracted_data": extracted_data,
                    "temp_image_path": temp_images[idx] if idx < len(temp_images) else page_result.get('temp_image_path'),
                    "status": "processing"
                })
                
                # Update temp_max_id for next page
                temp_max_id = new_id
            
            print(f"\n{'='*60}")
            created_count = len([p for p in page_placeholders if p.get('success')])
            print(f"📊 Placeholders Created: {created_count} of {len(page_placeholders)} pages (Status: processing)")
            if created_count == 0:
                return {
                    "success": False,
                    "message": "Failed to create any placeholders",
                    "error": "No placeholders were created"
                }
            print(f"{'='*60}")
            
            # ============================================
            # STEP 2: Process each page and update status to 'approved'
            # ============================================
            print(f"\n{'='*60}")
            print(f"🔄 STEP 2: Processing each page and updating status...")
            print(f"{'='*60}")
            
            successful_count = 0
            failed_count = 0
            
            for placeholder in page_placeholders:
                if not placeholder.get('success'):
                    processed_documents.append({
                        "success": False,
                        "error": placeholder.get('error', 'Unknown error'),
                        "page": placeholder.get('page', 0),
                        "status": "failed"
                    })
                    failed_count += 1
                    continue
                
                page_num = placeholder['page']
                page_document_id = placeholder['document_id']
                document_type = placeholder['document_type']
                image_filename = placeholder['image_filename']
                table_name = placeholder['table_name']
                extracted_data = placeholder['extracted_data']
                temp_image_path = placeholder.get('temp_image_path')
                
                print(f"\n   📄 Processing Page {page_num} (ID: {page_document_id})...")
                print(f"      Current Status: processing → (updating to approved)")
                
                # Save the actual image file
                if temp_image_path and os.path.exists(temp_image_path):
                    output_path = os.path.join(output_dir, image_filename)
                    
                    # Check if file already exists
                    if os.path.exists(output_path):
                        print(f"      ⚠️ File already exists: {image_filename}, overwriting...")
                        os.remove(output_path)
                    
                    # Copy the file from temp to permanent location
                    shutil.copy2(temp_image_path, output_path)
                    
                    # Verify the file was saved
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        print(f"      ✅ Image saved: {image_filename} ({file_size} bytes)")
                    else:
                        print(f"      ❌ Failed to save image: {image_filename}")
                else:
                    print(f"      ❌ ERROR: Temp image not found at {temp_image_path}")
                    # Try to find the temp image in alternate locations
                    alt_path = placeholder.get('image_path')
                    if alt_path and os.path.exists(alt_path):
                        output_path = os.path.join(output_dir, image_filename)
                        shutil.copy2(alt_path, output_path)
                        print(f"      ✅ Image saved from alt path: {image_filename}")
                    else:
                        print(f"      ❌ No valid temp image found for page {page_num}")
                
                # Update the placeholder with extracted data and change status to 'approved'
                if document_type == 'bank_cheque':
                    update_result = update_slip_document(
                        slip_id=page_document_id,
                        bank_cheque_name=extracted_data.get('bank_name'),
                        account_holder_name=extracted_data.get('pay'),
                        cheque_number=extracted_data.get('check_number'),
                        iban=extracted_data.get('iban'),
                        cheque_amount=extracted_data.get('amount'),
                        cheque_image_filename=image_filename
                    )
                elif document_type in ['bank_deposit_slip', 'bank_deposit_slips']:
                    update_result = update_deposit_document(
                        deposit_id=page_document_id,
                        bank_deposit_name=extracted_data.get('bank_name'),
                        account_title=extracted_data.get('account_title'),
                        account_number=extracted_data.get('account_number'),
                        depositor_name=extracted_data.get('depositor_name'),
                        contact_number=extracted_data.get('contact_number'),
                        cnic=extracted_data.get('cnic'),
                        deposit_amount=extracted_data.get('amount'),
                        deposit_image_filename=image_filename
                    )
                else:
                    update_result = update_receipt_document(
                        receipt_id=page_document_id,
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
                
                if update_result['success']:
                    processed_documents.append({
                        "success": True,
                        "document_id": page_document_id,
                        "image_name": image_filename,
                        "document_type": document_type,
                        "extracted_data": extracted_data,
                        "page": page_num,
                        "status": "approved"
                    })
                    print(f"      ✅ Updated successfully with image: {image_filename}")
                    successful_count += 1
                else:
                    update_document_status(page_document_id, table_name, 'failed')
                    processed_documents.append({
                        "success": False,
                        "error": update_result.get('error', 'Update failed'),
                        "document_id": page_document_id,
                        "page": page_num,
                        "status": "failed"
                    })
                    print(f"      ❌ Update failed for page {page_num}")
                    failed_count += 1
            
            # Return final response
            print(f"\n{'='*60}")
            print(f"📊 FINAL SUMMARY")
            print(f"{'='*60}")
            print(f"   Total Pages: {len(page_placeholders)}")
            print(f"   ✅ Successful: {successful_count}")
            print(f"   ❌ Failed: {failed_count}")
            print(f"{'='*60}")
            
            return {
                "success": True,
                "message": f"Placeholders created for {len(page_placeholders)} pages. Processed {successful_count} successfully, {failed_count} failed.",
                "total_pages": len(page_placeholders),
                "placeholder_created": len([p for p in page_placeholders if p.get('success')]),
                "successful_pages": successful_count,
                "failed_pages": failed_count,
                "documents": processed_documents
            }
        
        else:
            # Processing failed
            return {
                "success": False,
                "message": "Document processing failed",
                "error": result.get('error', 'Unknown error')
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ API Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Restore original cropped folder
        DocumentsConfig.CROPPED_FOLDER = original_cropped_folder
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"   Cleaned up temp file: {tmp_path}")
        # Clean up temp images
        if temp_images_for_pdf:
            for img in temp_images_for_pdf:
                if os.path.exists(img):
                    try:
                        os.remove(img)
                    except:
                        pass
        # Clean up crop session folder
        if os.path.exists(crop_session_folder):
            try:
                shutil.rmtree(crop_session_folder)
            except:
                pass


# ============================================
# GET ENDPOINTS (For Frontend Dashboard)
# ============================================

@router.get("/api/documents")
async def get_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all processed documents with pagination."""
    result = get_all_documents(limit=limit, offset=offset)
    
    if result['success']:
        return {
            "success": True,
            "count": len(result['documents']),
            "documents": result['documents']
        }
    else:
        return {
            "success": False,
            "count": 0,
            "documents": [],
            "error": result.get('error')
        }


@router.get("/api/documents/{document_id}")
async def get_document(document_id: int):
    """Get document by ID."""
    result = get_document_by_id(document_id)
    
    if result['success']:
        return result['document']
    else:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("/api/documents/search")
async def search_documents_endpoint(query: str = Query(..., min_length=1)):
    """Search documents by bank name, account title, or reference ID."""
    result = search_documents(query)
    
    if result['success']:
        return {
            "success": True,
            "count": len(result['results']),
            "results": result['results']
        }
    else:
        return {
            "success": False,
            "count": 0,
            "results": []
        }


@router.get("/api/documents/stats")
async def get_document_stats():
    """Get document processing statistics."""
    count_result = count_documents()
    last_id = get_last_document_id()
    
    next_id = last_id + 1 if last_id else 1
    
    return {
        "total_documents": count_result.get('count', 0) if count_result['success'] else 0,
        "last_document_id": last_id,
        "next_document_name": f"document_{next_id}",
        "storage_path": DOCUMENT_STORAGE_PATH
    }


@router.get("/api/documents/health")
async def documents_health_check():
    """Health check for document processing module."""
    try:
        processor = get_processor()
        return {
            "status": "healthy",
            "module": "document_processing",
            "processor": "ready",
            "storage_path": DOCUMENT_STORAGE_PATH
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "module": "document_processing",
            "error": str(e)
        }


# ============================================
# TESTING API (For Developers Only)
# ============================================

@router.post("/api/documents/test/process")
async def test_process_document(
    file: UploadFile = File(...),
    save_crops: bool = Query(False, description="Save cropped field images for debugging"),
    return_ocr_text: bool = Query(False, description="Include full OCR text in response"),
    return_metadata: bool = Query(True, description="Include processing metadata")
):
    """
    TESTING API - Process document with full debugging information.
    This endpoint is for developers only, not for frontend dashboard.
    """
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    test_output_dir = "data/test_output"
    os.makedirs(test_output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"test_{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(test_output_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    import time
    start_time = time.time()
    
    try:
        processor = get_processor()
        
        # Handle PDF for classification
        if file_ext == '.pdf':
            from app.services.document_pdf_service import pdf_to_document_images_continue
            temp_images = pdf_to_document_images_continue(file_path, start_from=1)
            if temp_images:
                classify_path = temp_images[0]
            else:
                classify_path = file_path
        else:
            classify_path = file_path
        
        doc_type, confidence = processor.classify_document(classify_path)
        
        if doc_type in ["bank_cheque", "bank_deposit_slip"]:
            result = processor.process_pipeline_a_with_details(
                file_path, doc_type, save_crops=save_crops
            )
            pipeline = "Pipeline A (Detection + Crop + OCR)"
        else:
            result = processor.process_pipeline_b_with_details(
                file_path, return_ocr_text=return_ocr_text
            )
            pipeline = "Pipeline B (Full OCR + Qwen)"
        
        processing_time = time.time() - start_time
        
        test_response = {
            "success": result.get("success", True),
            "testing_mode": True,
            "filename": file.filename,
            "timestamp": timestamp,
            "processing_info": {
                "pipeline": pipeline,
                "processing_time_seconds": round(processing_time, 3),
                "document_type": doc_type,
                "classification_confidence": confidence,
                "save_crops": save_crops,
                "return_ocr_text": return_ocr_text
            },
            "classification": {
                "document_type": doc_type,
                "confidence": confidence,
                "routed_to": pipeline
            },
            "extracted_data": result.get("extracted_data", {})
        }
        
        if "detection_details" in result:
            test_response["detection_details"] = result["detection_details"]
        
        if "ocr_details" in result:
            test_response["ocr_details"] = result["ocr_details"]
        
        if return_ocr_text and "full_ocr_text" in result:
            test_response["full_ocr_text"] = result["full_ocr_text"]
        
        if save_crops and "cropped_fields" in result:
            test_response["cropped_fields"] = result["cropped_fields"]
        
        if return_metadata:
            test_response["metadata"] = {
                "total_fields_extracted": len(result.get("extracted_data", {})),
                "fields_with_values": sum(1 for v in result.get("extracted_data", {}).values() if v),
                "processing_timestamp": datetime.now().isoformat(),
                "file_info": {
                    "original_name": file.filename,
                    "size_bytes": os.path.getsize(file_path),
                    "saved_path": file_path
                }
            }
        
        # Clean up temp classification image
        if file_ext == '.pdf' and temp_images and len(temp_images) > 0:
            for img in temp_images:
                try:
                    os.remove(img)
                except:
                    pass
        
        return JSONResponse(content=test_response)
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/api/documents/test/upload")
async def test_upload_document(
    file: UploadFile = File(...),
    save_crops: bool = Query(False, description="Save cropped field images for debugging"),
    return_ocr_text: bool = Query(False, description="Include full OCR text in response")
):
    """
    TESTING API - Upload PDF or image with full debugging information.
    This endpoint is for developers only, not for frontend dashboard.
    """
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        import time
        start_time = time.time()
        
        processor = DocumentProcessor()
        result = process_document_file(tmp_path, file.filename, processor, save_crops=save_crops, save_images=False)
        
        processing_time = time.time() - start_time
        
        debug_result = {
            "success": result['successful'] > 0 if result['type'] == 'pdf' else result['results'][0]['success'],
            "testing_mode": True,
            "filename": file.filename,
            "processing_time_seconds": round(processing_time, 3),
            "type": result['type']
        }
        
        if result['type'] == 'pdf':
            debug_result.update({
                "total_pages": result['total'],
                "successful_pages": result['successful'],
                "failed_pages": result['failed'],
                "start_number": result.get('start_number'),
                "end_number": result.get('end_number'),
                "documents": result['results']
            })
        else:
            r = result['results'][0]
            debug_result.update({
                "document_id": r.get('document_id'),
                "image_name": r.get('image_name'),
                "document_type": r.get('document_type'),
                "extracted_data": r.get('extracted_data')
            })
            if r.get('error'):
                debug_result["error"] = r.get('error')
        
        return JSONResponse(content=debug_result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/api/documents/test/info")
async def test_info():
    """Get information about testing endpoints (for developers)."""
    return {
        "purpose": "These endpoints are for developers only, not for frontend dashboard",
        "production_endpoints_for_frontend": {
            "bank_cheque": {
                "url": "POST /api/documents/upload/cheque",
                "description": "Upload Bank Cheque (Payment Slip)",
                "form_fields": {
                    "slip_name": "Document name (required)",
                    "rack_no": "Rack number (required)",
                    "voucher_number": "Voucher number (required)",
                    "cheque_image": "Image or PDF file (required)"
                }
            },
            "deposit_slip": {
                "url": "POST /api/documents/upload/deposit",
                "description": "Upload Deposit Slip",
                "form_fields": {
                    "deposit_name": "Document name (required)",
                    "rack_no": "Rack number (required)",
                    "voucher_number": "Voucher number (required)",
                    "deposit_image": "Image or PDF file (required)"
                }
            },
            "digital_receipt": {
                "url": "POST /api/documents/upload/receipt",
                "description": "Upload Digital Receipt",
                "form_fields": {
                    "receipt_name": "Document name (required)",
                    "rack_no": "Rack number (required)",
                    "voucher_number": "Voucher number (required)",
                    "digital_image": "Image or PDF file (required)"
                }
            },
            "list": "GET /api/documents",
            "get_by_id": "GET /api/documents/{id}",
            "search": "GET /api/documents/search?query=",
            "stats": "GET /api/documents/stats",
            "health": "GET /api/documents/health"
        },
        "testing_endpoints_for_developers": {
            "single_document_debug": {
                "url": "POST /api/documents/test/process",
                "description": "Process single document with full debugging",
                "query_params": {
                    "save_crops": "Save cropped field images (true/false)",
                    "return_ocr_text": "Include full OCR text in response (true/false)",
                    "return_metadata": "Include processing metadata (true/false)"
                }
            },
            "pdf_batch_debug": {
                "url": "POST /api/documents/test/upload",
                "description": "Upload PDF or image with batch processing and debugging",
                "query_params": {
                    "save_crops": "Save cropped field images for each page (true/false)",
                    "return_ocr_text": "Include full OCR text for each page (true/false)"
                }
            }
        },
        "naming_convention": {
            "bank_cheque": "cheque_X.jpg",
            "deposit_slip": "deposit_X.jpg",
            "digital_receipt": "receipt_X.jpg",
            "storage_path": DOCUMENT_STORAGE_PATH
        }
    }