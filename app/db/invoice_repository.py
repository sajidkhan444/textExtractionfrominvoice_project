"""Invoice database repository for local PostgreSQL."""

import json
import os
from datetime import datetime
from app.db.postgres_client import db


def get_last_invoice_id():
    """Get the last invoice ID from database (any invoice)."""
    try:
        query = "SELECT invoice_id FROM invoices ORDER BY invoice_id DESC LIMIT 1"
        result = db.execute_query(query, fetch_one=True)
        if result and result['invoice_id']:
            return result['invoice_id']
        return 0  # Return 0 if no invoices exist
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        return 0


def get_next_image_name():
    """Generate next sequential image name based on last invoice ID."""
    last_id = get_last_invoice_id()
    next_id = last_id + 1
    return f"inv_{next_id}.jpg"


def insert_invoice(company_name, phone_number, strn, ntn, order_number, 
                   invoice_number, invoice_date, clean_json, raw_ocr_json, image_path):
    """Insert a new invoice - only AI-relevant columns."""
    try:
        print(f"\n🔍 [DEBUG] insert_invoice called with:")
        print(f"   company_name: {company_name}")
        print(f"   invoice_number: {invoice_number}")
        print(f"   image_path: {image_path}")
        
        # Store just the filename in database (relative path)
        image_filename = os.path.basename(image_path)
        
        # Insert ONLY the columns we care about (invoicename will use DEFAULT)
        query = """
            INSERT INTO invoices (
                company_name, 
                phone_number, 
                strn, 
                ntn, 
                order_number, 
                invoice_number, 
                invoice_date, 
                clean_json, 
                raw_ocr_json, 
                invoice_image_path,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING invoice_id
        """
        
        params = (
            company_name if company_name else None,
            phone_number if phone_number else None,
            strn if strn else None,
            ntn if ntn else None,
            order_number if order_number else None,
            invoice_number if invoice_number else None,
            invoice_date if invoice_date else None,
            json.dumps(clean_json) if clean_json else None,
            json.dumps(raw_ocr_json) if raw_ocr_json else None,
            image_filename,
            datetime.now()
        )
        
        print(f"🔍 [DEBUG] Executing query with params length: {len(params)}")
        
        result = db.execute_query(query, params, fetch_one=True)
        
        print(f"🔍 [DEBUG] Query result: {result}")
        
        if result:
            print(f"   ✅ Database insert successful! ID: {result['invoice_id']}")
            return {
                'success': True,
                'id': result['invoice_id'],
                'image_path': image_filename
            }
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"   ❌ Database insert error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    


def get_all_invoices(limit=100, offset=0):
    """Get all invoices from database."""
    try:
        query = "SELECT * FROM invoices ORDER BY invoice_id DESC LIMIT %s OFFSET %s"
        result = db.execute_query(query, (limit, offset), fetch_all=True)
        return {'success': True, 'invoices': result}
    except Exception as e:
        return {'success': False, 'error': str(e), 'invoices': []}


def get_invoice_by_id(invoice_id):
    """Get invoice by ID."""
    try:
        query = "SELECT * FROM invoices WHERE invoice_id = %s"
        result = db.execute_query(query, (invoice_id,), fetch_one=True)
        if result:
            return {'success': True, 'invoice': result}
        return {'success': False, 'error': 'Invoice not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def count_invoices():
    """Count total invoices."""
    try:
        query = "SELECT COUNT(*) as count FROM invoices"
        result = db.execute_query(query, fetch_one=True)
        return {'success': True, 'count': result['count'] if result else 0}
    except Exception as e:
        return {'success': False, 'error': str(e), 'count': 0}


def search_invoices(search_query):
    """Search invoices by various fields."""
    try:
        query = """
            SELECT * FROM invoices 
            WHERE company_name ILIKE %s 
               OR ntn ILIKE %s 
               OR invoice_number ILIKE %s
               OR phone_number ILIKE %s
               OR strn ILIKE %s
            ORDER BY invoice_id DESC
            LIMIT 100
        """
        search_pattern = f"%{search_query}%"
        params = (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
        result = db.execute_query(query, params, fetch_all=True)
        return {'success': True, 'results': result}
    except Exception as e:
        return {'success': False, 'error': str(e), 'results': []}


def delete_invoice(invoice_id):
    """Delete an invoice by ID."""
    try:
        query = "DELETE FROM invoices WHERE invoice_id = %s RETURNING invoice_id"
        result = db.execute_query(query, (invoice_id,), fetch_one=True)
        if result:
            return {'success': True, 'deleted_id': result['invoice_id']}
        return {'success': False, 'error': 'Invoice not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def update_invoice_image_path(invoice_id, image_path):
    """Update the image path for an invoice."""
    try:
        image_filename = os.path.basename(image_path)
        query = """
            UPDATE invoices 
            SET invoice_image_path = %s 
            WHERE invoice_id = %s 
            RETURNING invoice_id
        """
        params = (image_filename, invoice_id)
        result = db.execute_query(query, params, fetch_one=True)
        if result:
            return {'success': True, 'updated_id': result['invoice_id']}
        return {'success': False, 'error': 'Invoice not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
    

# Add these functions at the end of the file

def get_last_completed_invoice_id():
    """Get the last invoice ID where invoice_image_path is NOT NULL (completed processing)."""
    try:
        query = """
            SELECT invoice_id FROM invoices 
            WHERE invoice_image_path IS NOT NULL 
            ORDER BY invoice_id DESC LIMIT 1
        """
        result = db.execute_query(query, fetch_one=True)
        if result and result['invoice_id']:
            return result['invoice_id']
        # If no completed invoice exists, return 0 (start from inv_1.jpg)
        return 0
    except Exception as e:
        print(f"⚠️ Database error in get_last_completed_invoice_id: {e}")
        return 0


def create_external_placeholder(invoicename, rack_no, voucher, date, image_path):
    """Create a placeholder row with metadata from other department."""
    try:
        query = """
            INSERT INTO invoices (
                invoicename,
                rack_no,
                voucher,
                date,
                image,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s::invoice_status)
            RETURNING invoice_id
        """
        
        params = (
            invoicename,
            rack_no,
            voucher,
            date,
            image_path,
            'processing'  # Valid enum value
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ External placeholder created! ID: {result['invoice_id']} (status: processing)")
            return {
                'success': True,
                'invoice_id': result['invoice_id']
            }
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"   ❌ External placeholder creation error: {e}")
        return {'success': False, 'error': str(e)}


def update_external_invoice(invoice_id, company_name, phone_number, strn, ntn, 
                             order_number, invoice_number, invoice_date, 
                             clean_json, raw_ocr_json, invoice_image_path):
    """Update existing external invoice with AI extraction results."""
    try:
        print(f"🔍 [DEBUG] Updating invoice_id: {invoice_id}")
        print(f"🔍 [DEBUG] invoice_image_path to save: {invoice_image_path}")
        
        # First check if the invoice exists
        check_query = "SELECT invoice_id FROM invoices WHERE invoice_id = %s"
        check_result = db.execute_query(check_query, (invoice_id,), fetch_one=True)
        
        if not check_result:
            print(f"   ❌ Invoice ID {invoice_id} not found in database!")
            return {'success': False, 'error': f'Invoice ID {invoice_id} not found'}
        
        query = """
            UPDATE invoices 
            SET company_name = %s,
                phone_number = %s,
                strn = %s,
                ntn = %s,
                order_number = %s,
                invoice_number = %s,
                invoice_date = %s,
                clean_json = %s,
                raw_ocr_json = %s,
                invoice_image_path = %s,
                created_at = %s
            WHERE invoice_id = %s
            RETURNING invoice_id
        """
        
        params = (
            company_name if company_name else None,
            phone_number if phone_number else None,
            strn if strn else None,
            ntn if ntn else None,
            order_number if order_number else None,
            invoice_number if invoice_number else None,
            invoice_date if invoice_date else None,
            json.dumps(clean_json) if clean_json else None,
            json.dumps(raw_ocr_json) if raw_ocr_json else None,
            invoice_image_path,
            datetime.now(),
            invoice_id
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ External invoice {invoice_id} updated with extraction results!")
            return {'success': True, 'invoice_id': result['invoice_id']}
        else:
            print(f"   ❌ No rows updated for invoice_id: {invoice_id}")
            return {'success': False, 'error': f'No rows updated for invoice_id {invoice_id}'}
            
    except Exception as e:
        print(f"   ❌ External update error: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    
    
def update_invoice_status(invoice_id, status):
    """Update the status of an invoice."""
    try:
        # Map status to valid enum values
        status_mapping = {
            'processing': 'processing',
            'approved': 'approved',
            'rejected': 'rejected',
            'failed': 'rejected',  # Map 'failed' to 'rejected'
            'completed': 'approved'  # Map 'completed' to 'approved'
        }
        
        db_status = status_mapping.get(status, status)
        
        query = """
            UPDATE invoices 
            SET status = %s::invoice_status
            WHERE invoice_id = %s
            RETURNING invoice_id
        """
        
        params = (db_status, invoice_id)
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Invoice {invoice_id} status updated to: {db_status}")
            return {'success': True}
        return {'success': False, 'error': f'Invoice {invoice_id} not found'}
    except Exception as e:
        print(f"   ❌ Status update error: {e}")
        return {'success': False, 'error': str(e)}
    
