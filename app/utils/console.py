"""Console utilities for pretty printing."""

def print_banner():
    """Print application banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ENHANCED INVOICE EXTRACTOR WITH SUPABASE                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SUPPORTS:                                                                   ║
║  ✅ Single Image Files (JPG, PNG, JPEG)                                      ║
║  ✅ Multi-page PDF Files                                                     ║
║                                                                              ║
║  PROCESSING:                                                                 ║
║  1. Upload file (image or PDF)                                              ║
║  2. Auto-detect file type                                                   ║
║  3. Get last DB ID → Generate sequential names (inv_X.jpg)                  ║
║  4. Extract text with EasyOCR                                               ║
║  5. Parse with Qwen AI                                                      ║
║  6. Store in local Database                                              ║
║  7. Upload image to local Storage                                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def print_success(message):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message):
    """Print info message."""
    print(f"ℹ️ {message}")


def print_warning(message):
    """Print warning message."""
    print(f"⚠️ {message}")