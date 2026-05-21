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

from app.services.document_processor import DocumentProcessor
from app.services.document_processor_service import process_document_file
from app.db.document_repository import (
    get_last_document_id, get_next_document_name, get_all_documents, 
    get_document_by_id, count_documents, search_documents,
    create_slip_placeholder, create_deposit_placeholder, create_receipt_placeholder,
    update_slip_document, update_deposit_document, update_receipt_document,
    update_document_status
)
from app.config import DOCUMENT_STORAGE_PATH
import uuid

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
# PRODUCTION API - For Frontend Dashboard
# ============================================

@router.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_name: str = Form(..., description="Document name (slip_name/deposit_name/receipt_name)"),
    rack_no: str = Form(..., description="Rack number"),
    voucher_number: str = Form(..., description="Voucher number"),
    return_crops: bool = Query(True, description="Return cropped field images for validation"),
    background_tasks: BackgroundTasks = None
):
    """
    PRODUCTION API - Frontend Dashboard Endpoint.
    
    First creates a placeholder row with metadata, then processes and updates.
    """
    from app.services.document_processor import DocumentProcessor
    from app.core.documents_config import DocumentsConfig
    
    # Generate a unique session ID for crops
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    # Create a session-specific crop folder
    crop_session_folder = os.path.join(DocumentsConfig.CROPPED_FOLDER, session_id)
    os.makedirs(crop_session_folder, exist_ok=True)
    
    # Temporarily override CROPPED_FOLDER for this session
    original_cropped_folder = DocumentsConfig.CROPPED_FOLDER
    if return_crops:
        DocumentsConfig.CROPPED_FOLDER = crop_session_folder
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
    
    if file_ext not in allowed_extensions:
        DocumentsConfig.CROPPED_FOLDER = original_cropped_folder
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
        # Step 1: Classify document to determine table
        processor = DocumentProcessor()
        doc_type, confidence = processor.classify_document(tmp_path)
        
        print(f"\n📋 Document classified as: {doc_type} (confidence: {confidence:.2%})")
        
        # Step 2: Create placeholder based on document type
        placeholder_result = None
        table_name = None
        document_id = None
        
        if doc_type == "bank_cheque":
            placeholder_result = create_slip_placeholder(document_name, rack_no, voucher_number, file.filename)
            table_name = "slip"
        elif doc_type == "bank_deposit_slips":
            placeholder_result = create_deposit_placeholder(document_name, rack_no, voucher_number, file.filename)
            table_name = "deposit"
        else:
            placeholder_result = create_receipt_placeholder(document_name, rack_no, voucher_number, file.filename)
            table_name = "receipt"
        
        if not placeholder_result['success']:
            raise HTTPException(status_code=500, detail=f"Failed to create placeholder: {placeholder_result['error']}")
        
        document_id = placeholder_result['id']
        print(f"✅ Placeholder created with ID: {document_id} in table: {table_name} (status: processing)")
        
        # Step 3: Process the document
        result = process_document_file(tmp_path, file.filename, processor)
        
        # Restore original cropped folder
        DocumentsConfig.CROPPED_FOLDER = original_cropped_folder
        
        # Get crop files if requested
        crop_files = []
        if return_crops and os.path.exists(crop_session_folder):
            for filename in os.listdir(crop_session_folder):
                if filename.endswith('.jpg'):
                    parts = filename.replace('.jpg', '').split('_')
                    if len(parts) >= 2:
                        field_name = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1]
                    else:
                        field_name = parts[0]
                    crop_files.append({
                        "field_name": field_name,
                        "filename": filename,
                        "url": f"/api/documents/crops/view/{session_id}/{filename}"
                    })
        
        # Step 4: Update placeholder with extraction results
        if result['type'] == 'image' and result['results'][0]['success']:
            r = result['results'][0]
            extracted_data = r.get('extracted_data', {})
            image_filename = r.get('image_name')
            document_type = r.get('document_type')
            
            update_result = None
            
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
            else:  # digital_receipt
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
                    "type": "image",
                    "message": "Extraction succeeded but database update failed",
                    "error": update_result.get('error'),
                    "document_id": document_id
                }
            
            return {
                "success": True,
                "type": "image",
                "message": "Document processed successfully",
                "document_id": document_id,
                "image_name": image_filename,
                "document_type": document_type,
                "extracted_data": extracted_data,
                "session_id": session_id,
                "metadata": {
                    "document_name": document_name,
                    "rack_no": rack_no,
                    "voucher_number": voucher_number
                },
                "crops": crop_files if return_crops else None,
                "crops_endpoint": f"/api/documents/crops/{session_id}" if return_crops else None
            }
        else:
            # Processing failed, update status
            update_document_status(document_id, table_name, 'failed')
            return {
                "success": False,
                "type": "image",
                "message": "Document processing failed",
                "error": result.get('error', 'Unknown error'),
                "document_id": document_id
            }
    
    except Exception as e:
        DocumentsConfig.CROPPED_FOLDER = original_cropped_folder
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ============================================
# CROP VALIDATION API (For UI Validation)
# ============================================

@router.get("/api/documents/crops/{session_id}")
async def get_cropped_images(session_id: str):
    """
    Retrieve cropped field images from a session for validation.
    
    Returns a list of cropped images with their field names.
    """
    from app.core.documents_config import DocumentsConfig
    
    crop_folder = os.path.join(DocumentsConfig.CROPPED_FOLDER, session_id)
    crop_files = []
    
    if os.path.exists(crop_folder):
        for filename in os.listdir(crop_folder):
            if filename.endswith('.jpg'):
                parts = filename.replace('.jpg', '').split('_')
                if len(parts) >= 2:
                    field_name = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1]
                else:
                    field_name = parts[0]
                
                file_path = os.path.join(crop_folder, filename)
                crop_files.append({
                    "field_name": field_name,
                    "filename": filename,
                    "url": f"/api/documents/crops/view/{session_id}/{filename}",
                    "size_bytes": os.path.getsize(file_path)
                })
    
    return {
        "success": True,
        "session_id": session_id,
        "total_crops": len(crop_files),
        "crops": crop_files
    }


@router.get("/api/documents/crops/view/{session_id}/{filename}")
async def view_cropped_image(session_id: str, filename: str):
    """
    View a specific cropped image from a session.
    """
    from app.core.documents_config import DocumentsConfig
    
    file_path = os.path.join(DocumentsConfig.CROPPED_FOLDER, session_id, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Cropped image not found")
    
    return FileResponse(file_path, media_type="image/jpeg")


@router.delete("/api/documents/crops/session/{session_id}")
async def delete_session_crops(session_id: str):
    """
    Delete cropped images for a specific session (cleanup).
    """
    from app.core.documents_config import DocumentsConfig
    import shutil
    
    session_folder = os.path.join(DocumentsConfig.CROPPED_FOLDER, session_id)
    
    if os.path.exists(session_folder):
        shutil.rmtree(session_folder)
        return {"success": True, "message": f"Session {session_id} crops deleted"}
    
    return {"success": False, "message": "Session not found"}


@router.get("/api/documents/crops/session/new")
async def get_new_session():
    """
    Get a new session ID for crop validation.
    """
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return {
        "success": True,
        "session_id": session_id,
        "message": "Use this session_id with return_crops=true parameter"
    }


# ============================================
# ADDITIONAL PRODUCTION ENDPOINTS
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
    next_name = get_next_document_name()
    
    return {
        "total_documents": count_result.get('count', 0) if count_result['success'] else 0,
        "last_document_id": last_id,
        "next_document_name": next_name,
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
# TESTING API (For Developers - Unchanged)
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
        doc_type, confidence = processor.classify_document(file_path)
        
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
    from app.services.document_processor_service import process_document_file
    from app.services.document_processor import DocumentProcessor
    
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
        result = process_document_file(tmp_path, file.filename, processor, save_crops=save_crops)
        
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
        "testing_endpoints": {
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
        "production_endpoints_for_frontend": {
            "upload": {
                "url": "POST /api/documents/upload",
                "description": "Upload PDF (all pages) or single image for processing",
                "form_fields": {
                    "document_name": "Document name (required)",
                    "rack_no": "Rack number (required)",
                    "voucher_number": "Voucher number (required)"
                },
                "query_params": {
                    "return_crops": "Return cropped field images for validation (true/false)"
                }
            },
            "list": "GET /api/documents",
            "get_by_id": "GET /api/documents/{id}",
            "search": "GET /api/documents/search",
            "stats": "GET /api/documents/stats",
            "health": "GET /api/documents/health"
        },
        "crop_validation_endpoints": {
            "get_crops": "GET /api/documents/crops/{session_id}",
            "view_crop": "GET /api/documents/crops/view/{session_id}/{filename}",
            "delete_crops": "DELETE /api/documents/crops/session/{session_id}",
            "new_session": "GET /api/documents/crops/session/new"
        },
        "naming_convention": {
            "single_image": "cheque_X.jpg / deposit_X.jpg / receipt_X.jpg",
            "pdf_pages": "cheque_{start_id}.jpg, deposit_{start_id+1}.jpg, ...",
            "storage_path": DOCUMENT_STORAGE_PATH
        }
    }