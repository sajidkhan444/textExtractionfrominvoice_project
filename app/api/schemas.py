"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime


class InvoiceExtractedData(BaseModel):
    """Extracted invoice data schema."""
    company_name: Optional[str] = None
    phone_number: Optional[str] = None
    strn: Optional[str] = None
    ntn: Optional[str] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None


class InvoiceSummary(BaseModel):
    """Summary of a single invoice in batch response."""
    invoice_id: Optional[int] = None
    image_name: Optional[str] = None
    company_name: Optional[str] = None
    phone_number: Optional[str] = None
    strn: Optional[str] = None
    ntn: Optional[str] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    success: Optional[bool] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response schema for upload (handles both image and PDF)."""
    success: bool
    type: str  # 'image' or 'pdf'
    message: str
    error: Optional[str] = None
    
    # For single image response
    invoice_id: Optional[int] = None
    image_name: Optional[str] = None
    extracted_data: Optional[InvoiceExtractedData] = None
    
    # For PDF response
    total_pages: Optional[int] = None
    successful_pages: Optional[int] = None
    failed_pages: Optional[int] = None
    start_number: Optional[int] = None
    end_number: Optional[int] = None
    invoices: Optional[List[InvoiceSummary]] = None


class InvoiceInfo(BaseModel):
    """Invoice information from database."""
    invoice_id: int
    company_name: Optional[str] = None
    phone_number: Optional[str] = None
    strn: Optional[str] = None
    ntn: Optional[str] = None
    order_number: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_image_path: Optional[str] = None
    created_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Response schema for search."""
    success: bool
    count: int
    results: List[InvoiceInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    storage: str
    version: str