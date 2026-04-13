"""Test PDF conversion."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_service import pdf_to_images_continue


def test_pdf_function_exists():
    """Test PDF function exists."""
    assert callable(pdf_to_images_continue)
    print("✅ PDF test passed!")


if __name__ == "__main__":
    test_pdf_function_exists()