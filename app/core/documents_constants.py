# app/core/documents_constants.py

from enum import Enum

class DocumentType(str, Enum):
    """Document types supported by the system"""
    BANK_DEPOSIT_SLIP = "bank_deposit_slips"
    BANK_CHEQUE = "bank_cheque"
    DIGITAL_TRANSACTION_RECEIPT = "digital_transaction_receipt"
    DIGITAL_BANK_RECEIPT = "digital_bank_receipt"
    UNKNOWN = "unknown"


class PipelineType(str, Enum):
    """Pipeline types for routing"""
    PIPELINE_A = "PIPELINE_A"  # Detection + Crop + OCR
    PIPELINE_B = "PIPELINE_B"  # Full OCR + Qwen


# Document to pipeline mapping
DOCUMENT_TO_PIPELINE = {
    DocumentType.BANK_DEPOSIT_SLIP: PipelineType.PIPELINE_A,
    DocumentType.BANK_CHEQUE: PipelineType.PIPELINE_A,
    DocumentType.DIGITAL_TRANSACTION_RECEIPT: PipelineType.PIPELINE_B,
    DocumentType.DIGITAL_BANK_RECEIPT: PipelineType.PIPELINE_B,
}


# Supported file extensions
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
SUPPORTED_PDF_EXTENSION = '.pdf'