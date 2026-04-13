"""Application dependencies."""

from app.core.model_loader import load_model_and_tokenizer
from app.ocr.smart_invoice_extractor import SmartInvoiceExtractor
from app.parser.qwen_invoice_parser import QwenInvoiceParser
from app.db.postgres_client import db

# Load Qwen model
model, tokenizer = load_model_and_tokenizer()

# Initialize extractor
extractor = SmartInvoiceExtractor()

# Initialize Qwen parser
qwen_parser = QwenInvoiceParser(model, tokenizer)

# Test database connection
if db.pool:
    print("✅ Database connection pool ready")
else:
    print("⚠️ Database not connected")