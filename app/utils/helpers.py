"""Helper utilities."""

import os
import re
from pathlib import Path


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_filename(filename):
    """Clean filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_file_extension(filepath):
    """Get file extension."""
    return Path(filepath).suffix.lower()