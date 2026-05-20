# app/dependencies.py

from app.core.model_loader import load_model_and_tokenizer
from app.ocr.smart_invoice_extractor import SmartInvoiceExtractor
from app.parser.qwen_invoice_parser import QwenInvoiceParser
from app.db.postgres_client import db

# Load Qwen model (this happens first)
model, tokenizer = load_model_and_tokenizer()

# Initialize extractor
extractor = SmartInvoiceExtractor()

# Initialize Qwen invoice parser
qwen_parser = QwenInvoiceParser(model, tokenizer)

# Initialize document parser (reuses the same model)
from app.parser.qwen_document_parser import QwenDocumentParser
document_parser = QwenDocumentParser(model, tokenizer)

# Test database connection
if db.pool:
    print("✅ Database connection pool ready")
else:
    print("⚠️ Database not connected")