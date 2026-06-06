# app/db/document_repository.py

import os
import re
from datetime import datetime
from typing import Dict
from app.db.postgres_client import db


# ============================================
# BANK CHEQUE TABLE (slip) - PLACEHOLDER & UPDATE
# ============================================

def get_last_cheque_id():
    """Get the last cheque ID from database."""
    try:
        query = "SELECT COALESCE(MAX(id), 0) as max_id FROM slip"
        result = db.execute_query(query, fetch_one=True)
        return result['max_id'] if result else 0
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        return 0


def get_next_cheque_name():
    """Generate next sequential cheque name."""
    last_id = get_last_cheque_id()
    next_id = last_id + 1
    return f"cheque_{next_id}.jpg"


def create_slip_placeholder(slip_name, rack_no, voucher_number, image_path):
    """Create a placeholder row in slip table with metadata and return the ID."""
    try:
        query = """
            INSERT INTO slip (
                slip_name,
                rack_no,
                voucher_number,
                cheque_image,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            slip_name,
            rack_no,
            voucher_number,
            image_path,
            'processing',
            datetime.now()
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            new_id = result['id']
            print(f"   ✅ Slip placeholder created! ID: {new_id} (status: processing)")
            return {'success': True, 'id': new_id}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"   ❌ Slip placeholder creation error: {e}")
        return {'success': False, 'error': str(e)}


def update_slip_document(
    slip_id,
    bank_cheque_name,
    account_holder_name,
    cheque_number,
    iban,
    cheque_amount,
    cheque_image_filename
):
    """Update existing slip placeholder with extraction results."""
    try:
        query = """
            UPDATE slip 
            SET bank_cheque_name = %s,
                account_holder_name = %s,
                cheque_number = %s,
                iban = %s,
                cheque_amount = %s,
                cheque_image = %s,
                status = 'approved'
            WHERE id = %s
            RETURNING id
        """
        
        params = (
            bank_cheque_name,
            account_holder_name,
            cheque_number,
            iban,
            cheque_amount,
            cheque_image_filename,
            slip_id
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Slip {slip_id} updated with extraction results! Status: approved")
            return {'success': True, 'id': result['id']}
        return {'success': False, 'error': f'No rows updated for slip_id {slip_id}'}
    except Exception as e:
        print(f"   ❌ Slip update error: {e}")
        return {'success': False, 'error': str(e)}


def insert_cheque_document(
    bank_cheque_name,
    account_holder_name,
    cheque_number,
    iban,
    cheque_amount,
    cheque_image_filename
):
    """Direct insert for bank cheque (legacy - use placeholder/update pattern instead)."""
    try:
        query = """
            INSERT INTO slip (
                bank_cheque_name,
                account_holder_name,
                cheque_number,
                iban,
                cheque_amount,
                cheque_image,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            bank_cheque_name,
            account_holder_name,
            cheque_number,
            iban,
            cheque_amount,
            cheque_image_filename,
            'approved',
            datetime.now()
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': cheque_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (cheque): {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# DEPOSIT SLIP TABLE (deposit) - PLACEHOLDER & UPDATE
# ============================================

def get_last_deposit_id():
    """Get the last deposit ID from database."""
    try:
        query = "SELECT COALESCE(MAX(id), 0) as max_id FROM deposit"
        result = db.execute_query(query, fetch_one=True)
        return result['max_id'] if result else 0
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        return 0


def get_next_deposit_name():
    """Generate next sequential deposit slip name."""
    last_id = get_last_deposit_id()
    next_id = last_id + 1
    return f"deposit_{next_id}.jpg"


def create_deposit_placeholder(deposit_name, rack_no, voucher_number, image_path):
    """Create a placeholder row in deposit table with metadata."""
    try:
        query = """
            INSERT INTO deposit (
                deposit_name,
                rack_no,
                voucher_number,
                deposit_image,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            deposit_name,
            rack_no,
            voucher_number,
            image_path,
            'processing',
            datetime.now()
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Deposit placeholder created! ID: {result['id']} (status: processing)")
            return {'success': True, 'id': result['id']}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"   ❌ Deposit placeholder creation error: {e}")
        return {'success': False, 'error': str(e)}


def update_deposit_document(
    deposit_id,
    bank_deposit_name,
    account_title,
    account_number,
    depositor_name,
    contact_number,
    cnic,
    deposit_amount,
    deposit_image_filename
):
    """Update existing deposit placeholder with extraction results."""
    try:
        query = """
            UPDATE deposit 
            SET bank_deposit_name = %s,
                account_title = %s,
                account_number = %s,
                depositor_name = %s,
                contact_number = %s,
                cnic = %s,
                deposit_amount = %s,
                deposit_image = %s,
                status = 'approved'
            WHERE id = %s
            RETURNING id
        """
        
        params = (
            bank_deposit_name,
            account_title,
            account_number,
            depositor_name,
            contact_number,
            cnic,
            deposit_amount,
            deposit_image_filename,
            deposit_id
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Deposit {deposit_id} updated with extraction results! Status: approved")
            return {'success': True, 'id': result['id']}
        return {'success': False, 'error': f'No rows updated for deposit_id {deposit_id}'}
    except Exception as e:
        print(f"   ❌ Deposit update error: {e}")
        return {'success': False, 'error': str(e)}


def insert_deposit_slip_document(
    bank_deposit_name,
    account_title,
    account_number,
    depositor_name,
    contact_number,
    cnic,
    deposit_amount,
    deposit_image_filename,
    serial_number=None
):
    """Direct insert for deposit slip (legacy - use placeholder/update pattern instead)."""
    try:
        query = """
            INSERT INTO deposit (
                bank_deposit_name,
                account_title,
                account_number,
                depositor_name,
                contact_number,
                cnic,
                deposit_amount,
                deposit_image,
                serial_number,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            bank_deposit_name,
            account_title,
            account_number,
            depositor_name,
            contact_number,
            cnic,
            deposit_amount,
            deposit_image_filename,
            serial_number,
            'approved',
            datetime.now()
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': deposit_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (deposit slip): {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# DIGITAL RECEIPT TABLE (receipt) - PLACEHOLDER & UPDATE
# ============================================

def get_last_receipt_id():
    """Get the last receipt ID from database."""
    try:
        query = "SELECT COALESCE(MAX(id), 0) as max_id FROM receipt"
        result = db.execute_query(query, fetch_one=True)
        return result['max_id'] if result else 0
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        return 0


def get_next_receipt_name():
    """Generate next sequential receipt name."""
    last_id = get_last_receipt_id()
    next_id = last_id + 1
    return f"receipt_{next_id}.jpg"


def create_receipt_placeholder(receipt_name, rack_no, voucher_number, image_path):
    """Create a placeholder row in receipt table with metadata."""
    try:
        query = """
            INSERT INTO receipt (
                receipt_name,
                rack_no,
                voucher_number,
                digital_image,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            receipt_name,
            rack_no,
            voucher_number,
            image_path,
            'processing',
            datetime.now()
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Receipt placeholder created! ID: {result['id']} (status: processing)")
            return {'success': True, 'id': result['id']}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"   ❌ Receipt placeholder creation error: {e}")
        return {'success': False, 'error': str(e)}


def update_receipt_document(
    receipt_id,
    bank_digital_name,
    digital_amount,
    sender_name,
    receiver_name,
    reference_id,
    phone_number,
    payment_date,
    payment_time,
    digital_image_filename
):
    """Update existing receipt placeholder with extraction results."""
    try:
        query = """
            UPDATE receipt 
            SET bank_digital_name = %s,
                digital_amount = %s,
                sender_name = %s,
                receiver_name = %s,
                reference_id = %s,
                phone_number = %s,
                payment_date = %s,
                payment_time = %s,
                digital_image = %s,
                status = 'approved'
            WHERE id = %s
            RETURNING id
        """
        
        params = (
            bank_digital_name,
            digital_amount,
            sender_name,
            receiver_name,
            reference_id,
            phone_number,
            payment_date,
            payment_time,
            digital_image_filename,
            receipt_id
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Receipt {receipt_id} updated with extraction results! Status: approved")
            return {'success': True, 'id': result['id']}
        return {'success': False, 'error': f'No rows updated for receipt_id {receipt_id}'}
    except Exception as e:
        print(f"   ❌ Receipt update error: {e}")
        return {'success': False, 'error': str(e)}


def insert_digital_receipt_document(
    bank_digital_name,
    digital_amount,
    sender_name,
    receiver_name,
    reference_id,
    phone_number,
    payment_date,
    payment_time,
    digital_image_filename
):
    """Direct insert for digital receipt (legacy - use placeholder/update pattern instead)."""
    try:
        query = """
            INSERT INTO receipt (
                bank_digital_name,
                digital_amount,
                sender_name,
                receiver_name,
                reference_id,
                phone_number,
                payment_date,
                payment_time,
                digital_image,
                status,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            bank_digital_name,
            digital_amount,
            sender_name,
            receiver_name,
            reference_id,
            phone_number,
            payment_date,
            payment_time,
            digital_image_filename,
            'approved',
            datetime.now()
        )
        
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': digital_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (digital receipt): {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# STATUS UPDATE FUNCTIONS
# ============================================

def update_document_status(document_id, table_name, status):
    """Update the status of a document."""
    try:
        # Validate table name to prevent SQL injection
        if table_name not in ['slip', 'deposit', 'receipt']:
            raise ValueError(f"Invalid table name: {table_name}")
        
        # Validate status
        if status not in ['processing', 'approved', 'failed']:
            status = 'failed'
        
        query = f"""
            UPDATE {table_name} 
            SET status = %s
            WHERE id = %s
            RETURNING id
        """
        
        params = (status, document_id)
        # execute_query already handles commit internally
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            print(f"   ✅ Document {document_id} status updated to: {status}")
            return {'success': True}
        return {'success': False, 'error': f'Document {document_id} not found'}
    except Exception as e:
        print(f"   ❌ Status update error: {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# SEARCH FUNCTION
# ============================================

def search_documents(search_query):
    """Search documents across all tables."""
    try:
        search_pattern = f"%{search_query}%"
        
        # Search in slip table (bank cheques)
        slip_query = """
            SELECT id, 'cheque' as type, bank_cheque_name as bank_name, 
                   account_holder_name as account_name, cheque_number,
                   cheque_amount as amount, cheque_image as image, status, created_at
            FROM slip 
            WHERE bank_cheque_name ILIKE %s 
               OR account_holder_name ILIKE %s 
               OR cheque_number ILIKE %s
               OR iban ILIKE %s
               OR slip_name ILIKE %s
               OR rack_no ILIKE %s
               OR voucher_number ILIKE %s
        """
        slip_params = (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)
        slip_results = db.execute_query(slip_query, slip_params, fetch_all=True) or []
        
        # Search in deposit table
        deposit_query = """
            SELECT id, 'deposit' as type, bank_deposit_name as bank_name,
                   account_title as account_name, account_number, depositor_name,
                   deposit_amount as amount, deposit_image as image, status, created_at
            FROM deposit 
            WHERE bank_deposit_name ILIKE %s 
               OR account_title ILIKE %s 
               OR account_number ILIKE %s
               OR depositor_name ILIKE %s
               OR cnic ILIKE %s
               OR contact_number ILIKE %s
               OR deposit_name ILIKE %s
               OR rack_no ILIKE %s
               OR voucher_number ILIKE %s
        """
        deposit_params = (search_pattern,) * 9
        deposit_results = db.execute_query(deposit_query, deposit_params, fetch_all=True) or []
        
        # Search in receipt table
        receipt_query = """
            SELECT id, 'receipt' as type, bank_digital_name as bank_name,
                   sender_name as account_name, receiver_name, reference_id,
                   digital_amount as amount, digital_image as image, status, created_at
            FROM receipt 
            WHERE bank_digital_name ILIKE %s 
               OR sender_name ILIKE %s 
               OR receiver_name ILIKE %s
               OR reference_id ILIKE %s
               OR phone_number ILIKE %s
               OR receipt_name ILIKE %s
               OR rack_no ILIKE %s
               OR voucher_number ILIKE %s
        """
        receipt_params = (search_pattern,) * 8
        receipt_results = db.execute_query(receipt_query, receipt_params, fetch_all=True) or []
        
        # Combine all results
        all_results = slip_results + deposit_results + receipt_results
        
        # Sort by created_at descending
        all_results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {'success': True, 'results': all_results}
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {'success': False, 'error': str(e), 'results': []}


# ============================================
# COMMON FUNCTIONS (for compatibility)
# ============================================

def get_last_document_id():
    """Get the last document ID (for compatibility)."""
    try:
        query = """
            SELECT COALESCE(
                (SELECT MAX(id) FROM slip),
                (SELECT MAX(id) FROM deposit),
                (SELECT MAX(id) FROM receipt),
                0
            ) as max_id
        """
        result = db.execute_query(query, fetch_one=True)
        if result and result['max_id'] is not None:
            return result['max_id']
        return 0
    except Exception as e:
        print(f"⚠️ Database error: {e}")
        return 0


def get_next_document_name():
    """Generate next sequential document name (for compatibility)."""
    last_id = get_last_document_id()
    if last_id is None:
        last_id = 0
    next_id = last_id + 1
    return f"payment_slip_{next_id}.jpg"


def get_all_documents(limit=100, offset=0):
    """Get all documents from all tables."""
    try:
        query = """
            SELECT id, 'cheque' as type, bank_cheque_name as bank_name, 
                   account_holder_name as account_name, status, created_at
            FROM slip
            UNION ALL
            SELECT id, 'deposit' as type, bank_deposit_name as bank_name,
                   account_title as account_name, status, created_at
            FROM deposit
            UNION ALL
            SELECT id, 'receipt' as type, bank_digital_name as bank_name,
                   sender_name as account_name, status, created_at
            FROM receipt
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        result = db.execute_query(query, (limit, offset), fetch_all=True)
        return {'success': True, 'documents': result if result else []}
    except Exception as e:
        return {'success': False, 'error': str(e), 'documents': []}


def get_document_by_id(document_id):
    """Get document by ID from any table."""
    try:
        # Try slip table
        query = "SELECT *, 'cheque' as type FROM slip WHERE id = %s"
        result = db.execute_query(query, (document_id,), fetch_one=True)
        if result:
            return {'success': True, 'document': result}
        
        # Try deposit table
        query = "SELECT *, 'deposit' as type FROM deposit WHERE id = %s"
        result = db.execute_query(query, (document_id,), fetch_one=True)
        if result:
            return {'success': True, 'document': result}
        
        # Try receipt table
        query = "SELECT *, 'receipt' as type FROM receipt WHERE id = %s"
        result = db.execute_query(query, (document_id,), fetch_one=True)
        if result:
            return {'success': True, 'document': result}
        
        return {'success': False, 'error': 'Document not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def count_documents():
    """Count total documents across all tables."""
    try:
        query = """
            SELECT 
                COALESCE((SELECT COUNT(*) FROM slip), 0) +
                COALESCE((SELECT COUNT(*) FROM deposit), 0) +
                COALESCE((SELECT COUNT(*) FROM receipt), 0) as total
        """
        result = db.execute_query(query, fetch_one=True)
        return {'success': True, 'count': result['total'] if result else 0}
    except Exception as e:
        return {'success': False, 'error': str(e), 'count': 0}


# ============================================
# FUNCTION: Get Current Max ID Across All Tables
# ============================================

def get_current_max_id() -> Dict:
    """
    Get the current maximum ID from slip, deposit, and receipt tables.
    
    This function is used for generating unique sequential IDs across all document types.
    Each call returns the current MAX ID, which should be used before creating a new record.
    
    IMPORTANT: For PDF pages, call this function BEFORE each page to get a fresh ID.
    
    Returns:
        Dict with 'success' and 'max_id' (or 'error')
        Example: {"success": True, "max_id": 17}
    """
    try:
        # Query to get maximum ID across all three tables
        query = """
            SELECT COALESCE(MAX(id), 0) as max_id FROM (
                SELECT id FROM slip
                UNION ALL
                SELECT id FROM deposit
                UNION ALL
                SELECT id FROM receipt
            ) as all_ids
        """
        
        result = db.execute_query(query, fetch_one=True)
        
        if result and 'max_id' in result:
            max_id = result['max_id']
            print(f"   📊 Current MAX ID across all tables: {max_id}")
            return {"success": True, "max_id": max_id}
        else:
            return {"success": True, "max_id": 0}
    
    except Exception as e:
        print(f"⚠️ Error getting current max ID: {e}")
        return {"success": False, "error": str(e), "max_id": 0}
    
# # Add these functions to document_repository.py (after existing functions)

# def get_last_slip_id_dict() -> Dict:
#     """Get the last ID from slip table (bank cheques) as Dict."""
#     try:
#         query = "SELECT COALESCE(MAX(id), 0) as max_id FROM slip"
#         result = db.execute_query(query, fetch_one=True)
#         max_id = result['max_id'] if result else 0
#         print(f"   📊 Last slip ID (bank cheque): {max_id}")
#         return {"success": True, "max_id": max_id}
#     except Exception as e:
#         print(f"⚠️ Error getting last slip ID: {e}")
#         return {"success": False, "error": str(e), "max_id": 0}


# def get_last_deposit_id_dict() -> Dict:
#     """Get the last ID from deposit table as Dict."""
#     try:
#         query = "SELECT COALESCE(MAX(id), 0) as max_id FROM deposit"
#         result = db.execute_query(query, fetch_one=True)
#         max_id = result['max_id'] if result else 0
#         print(f"   📊 Last deposit ID: {max_id}")
#         return {"success": True, "max_id": max_id}
#     except Exception as e:
#         print(f"⚠️ Error getting last deposit ID: {e}")
#         return {"success": False, "error": str(e), "max_id": 0}


# def get_last_receipt_id_dict() -> Dict:
#     """Get the last ID from receipt table as Dict."""
#     try:
#         query = "SELECT COALESCE(MAX(id), 0) as max_id FROM receipt"
#         result = db.execute_query(query, fetch_one=True)
#         max_id = result['max_id'] if result else 0
#         print(f"   📊 Last receipt ID: {max_id}")
#         return {"success": True, "max_id": max_id}
#     except Exception as e:
#         print(f"⚠️ Error getting last receipt ID: {e}")
#         return {"success": False, "error": str(e), "max_id": 0}