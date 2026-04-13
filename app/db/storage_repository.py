"""Local storage repository for invoice images."""

import os
import shutil
from app.config import LOCAL_STORAGE_PATH


def ensure_storage_dir():
    """Ensure storage directory exists."""
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)


def upload_image_to_storage(local_image_path, image_filename):
    """Copy image to local storage folder."""
    try:
        ensure_storage_dir()
        
        # Destination path
        dest_path = os.path.join(LOCAL_STORAGE_PATH, image_filename)
        
        # Copy file
        shutil.copy2(local_image_path, dest_path)
        
        print(f"   ✅ Image saved to: {dest_path}")
        
        return {
            'success': True,
            'filename': image_filename,
            'url': dest_path,
            'local_path': dest_path
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_image_path(image_filename):
    """Get full local path for an image."""
    return os.path.join(LOCAL_STORAGE_PATH, image_filename)


def get_image_url(image_filename):
    """Get URL/path for an image."""
    return os.path.join(LOCAL_STORAGE_PATH, image_filename)


def list_all_images():
    """List all images in local storage."""
    try:
        ensure_storage_dir()
        images = []
        for filename in os.listdir(LOCAL_STORAGE_PATH):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(LOCAL_STORAGE_PATH, filename)
                stat = os.stat(file_path)
                images.append({
                    'name': filename,
                    'metadata': {'size': stat.st_size},
                    'created_at': stat.st_ctime
                })
        return {'success': True, 'images': images}
    except Exception as e:
        return {'success': False, 'error': str(e), 'images': []}


def delete_image(image_filename):
    """Delete an image from local storage."""
    try:
        file_path = os.path.join(LOCAL_STORAGE_PATH, image_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {'success': True}
        return {'success': False, 'error': 'File not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def image_exists(image_filename):
    """Check if an image exists in storage."""
    file_path = os.path.join(LOCAL_STORAGE_PATH, image_filename)
    return os.path.exists(file_path)