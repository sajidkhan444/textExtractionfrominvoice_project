# app/db/document_repository.py

import os
import re
from datetime import datetime
from app.db.postgres_client import db


# ============================================
# BANK CHEQUE TABLE (slip)
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


def insert_cheque_document(
    bank_cheque_name,
    account_holder_name,
    cheque_number,
    iban,
    cheque_amount,
    cheque_image_filename
):
    """Insert bank cheque extraction result into slip table."""
    try:
        query = """
            INSERT INTO slip (
                bank_cheque_name,
                account_holder_name,
                cheque_number,
                iban,
                cheque_amount,
                cheque_image,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            bank_cheque_name,
            account_holder_name,
            cheque_number,
            iban,
            cheque_amount,
            cheque_image_filename,
            datetime.now()
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': cheque_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (cheque): {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# DEPOSIT SLIP TABLE (deposit)
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
    """Insert deposit slip extraction result into deposit table."""
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
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            datetime.now()
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': deposit_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (deposit slip): {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# DIGITAL RECEIPT TABLE (receipt)
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
    """Insert digital receipt extraction result into receipt table."""
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
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            datetime.now()
        )
        
        result = db.execute_query(query, params, fetch_one=True)
        
        if result:
            return {'success': True, 'id': result['id'], 'image_path': digital_image_filename}
        return {'success': False, 'error': 'No data returned'}
    except Exception as e:
        print(f"❌ Database insert error (digital receipt): {e}")
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
                   cheque_amount as amount, cheque_image as image, created_at
            FROM slip 
            WHERE bank_cheque_name ILIKE %s 
               OR account_holder_name ILIKE %s 
               OR cheque_number ILIKE %s
               OR iban ILIKE %s
        """
        slip_params = (search_pattern, search_pattern, search_pattern, search_pattern)
        slip_results = db.execute_query(slip_query, slip_params, fetch_all=True) or []
        
        # Search in deposit table
        deposit_query = """
            SELECT id, 'deposit' as type, bank_deposit_name as bank_name,
                   account_title as account_name, account_number, depositor_name,
                   deposit_amount as amount, deposit_image as image, created_at
            FROM deposit 
            WHERE bank_deposit_name ILIKE %s 
               OR account_title ILIKE %s 
               OR account_number ILIKE %s
               OR depositor_name ILIKE %s
               OR cnic ILIKE %s
               OR contact_number ILIKE %s
        """
        deposit_params = (search_pattern,) * 6
        deposit_results = db.execute_query(deposit_query, deposit_params, fetch_all=True) or []
        
        # Search in receipt table
        receipt_query = """
            SELECT id, 'receipt' as type, bank_digital_name as bank_name,
                   sender_name as account_name, receiver_name, reference_id,
                   digital_amount as amount, digital_image as image, created_at
            FROM receipt 
            WHERE bank_digital_name ILIKE %s 
               OR sender_name ILIKE %s 
               OR receiver_name ILIKE %s
               OR reference_id ILIKE %s
               OR phone_number ILIKE %s
        """
        receipt_params = (search_pattern,) * 5
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
    # Ensure last_id is an integer
    if last_id is None:
        last_id = 0
    next_id = last_id + 1
    return f"payment_slip_{next_id}.jpg"


def get_all_documents(limit=100, offset=0):
    """Get all documents from all tables."""
    try:
        query = """
            SELECT id, 'cheque' as type, bank_cheque_name as bank_name, 
                   account_holder_name as account_name, created_at
            FROM slip
            UNION ALL
            SELECT id, 'deposit' as type, bank_deposit_name as bank_name,
                   account_title as account_name, created_at
            FROM deposit
            UNION ALL
            SELECT id, 'receipt' as type, bank_digital_name as bank_name,
                   sender_name as account_name, created_at
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