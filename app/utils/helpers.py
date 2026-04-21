"""Helper utilities."""

import os
import re
from pathlib import Path
from app.config import PROCESSED_INVOICES_PATH


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_filename(filename):
    """Clean filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_file_extension(filepath):
    """Get file extension."""
    return Path(filepath).suffix.lower()


def get_unique_filename(base_filename):
    """
    Check if filename exists in filesystem.
    If exists, append _1, _2, etc. to make it unique.
    Always ensures .jpg extension.
    """
    # Ensure base_filename has .jpg extension
    if not base_filename.endswith('.jpg'):
        base_filename = base_filename.rsplit('.', 1)[0] + '.jpg'
    
    name_without_ext = base_filename.rsplit('.', 1)[0]
    extension = '.jpg'  # Force .jpg extension
    
    # Check if file exists in filesystem
    file_path = os.path.join(PROCESSED_INVOICES_PATH, base_filename)
    
    if not os.path.exists(file_path):
        return base_filename
    
    # File exists, find a unique number
    counter = 1
    while True:
        new_filename = f"{name_without_ext}_{counter}{extension}"
        new_file_path = os.path.join(PROCESSED_INVOICES_PATH, new_filename)
        if not os.path.exists(new_file_path):
            print(f"   ⚠️ Filename '{base_filename}' already exists, using '{new_filename}'")
            return new_filename
        counter += 1


def generate_filename_from_company(company_name, fallback_name, invoice_id):
    """
    Generate a clean filename from company name with .jpg extension.
    """
    # First priority: Use company name if found
    if company_name and company_name != 'N/A' and company_name != 'None' and str(company_name).strip():
        name = str(company_name).lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')
        if len(name) > 50:
            name = name[:50]
        base_filename = f"{name}.jpg"
        return get_unique_filename(base_filename)
    
    # Second priority: Use invoicename from department
    elif fallback_name and str(fallback_name).strip():
        name = str(fallback_name).lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')
        if len(name) > 50:
            name = name[:50]
        base_filename = f"{name}.jpg"
        return get_unique_filename(base_filename)
    
    # Last resort: Use sequential naming
    else:
        base_filename = f"inv_{invoice_id}.jpg"
        return get_unique_filename(base_filename)