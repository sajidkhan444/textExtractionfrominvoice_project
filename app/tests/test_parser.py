"""Test Qwen parser."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_parser_import():
    """Test parser import."""
    from app.parser.qwen_invoice_parser import QwenInvoiceParser
    assert QwenInvoiceParser is not None
    print("✅ Parser test passed!")


if __name__ == "__main__":
    test_parser_import()