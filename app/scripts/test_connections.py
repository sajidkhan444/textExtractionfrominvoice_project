"""Test script for local PostgreSQL and storage connections."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.connection_test_service import test_database_connection, test_storage_connection


def main():
    print("Testing Local Connections...")
    print("="*50)
    
    test_database_connection()
    test_storage_connection()
    
    print("\n✅ Connection tests complete!")


if __name__ == "__main__":
    main()