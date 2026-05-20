# app/db/document_storage_repository.py

import os
import shutil
from app.core.documents_config import DocumentsConfig


def ensure_output_dir():
    """Ensure output directory exists"""
    os.makedirs(DocumentsConfig.OUTPUT_FOLDER, exist_ok=True)


def save_processed_image(source_image_path, image_filename):
    """
    Save processed image to permanent storage.
    
    Args:
        source_image_path: Path to the temporary processed image
        image_filename: Permanent filename (e.g., payment_slip_17.jpg)
    
    Returns:
        dict with success status and file info
    """
    try:
        ensure_output_dir()
        
        # Destination path using the permanent filename
        dest_path = os.path.join(DocumentsConfig.OUTPUT_FOLDER, image_filename)
        
        # Copy file from temp location to permanent location
        shutil.copy2(source_image_path, dest_path)
        
        print(f"   ✅ Image saved permanently: {image_filename}")
        print(f"   📁 Location: {dest_path}")
        
        return {
            'success': True,
            'filename': image_filename,
            'path': dest_path
        }
    except Exception as e:
        print(f"   ❌ Failed to save image: {e}")
        return {'success': False, 'error': str(e)}


def get_processed_image_path(image_filename):
    """Get full local path for a processed image."""
    return os.path.join(DocumentsConfig.OUTPUT_FOLDER, image_filename)


def delete_processed_image(image_filename):
    """Delete a processed image from storage."""
    try:
        file_path = os.path.join(DocumentsConfig.OUTPUT_FOLDER, image_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {'success': True}
        return {'success': False, 'error': 'File not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}