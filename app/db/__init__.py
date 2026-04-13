"""Database package."""

"""Database package for local PostgreSQL."""

from app.db.postgres_client import db
from app.db.invoice_repository import (
    get_last_invoice_id,
    get_next_image_name,
    insert_invoice,
    get_all_invoices,
    get_invoice_by_id,
    count_invoices,
    search_invoices,
    delete_invoice,
    update_invoice_image_path
)
from app.db.storage_repository import (
    upload_image_to_storage,
    get_image_path,
    get_image_url,
    list_all_images,
    delete_image,
    image_exists,
    ensure_storage_dir
)

__all__ = [
    'db',
    'get_last_invoice_id',
    'get_next_image_name',
    'insert_invoice',
    'get_all_invoices',
    'get_invoice_by_id',
    'count_invoices',
    'search_invoices',
    'delete_invoice',
    'update_invoice_image_path',
    'upload_image_to_storage',
    'get_image_path',
    'get_image_url',
    'list_all_images',
    'delete_image',
    'image_exists',
    'ensure_storage_dir'
]