# app/db/postgres_client.py
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import os
from dotenv import load_dotenv

load_dotenv()

class PostgresClient:
    def __init__(self):
        self.pool = None
        self.connect()
    
    def connect(self):
        try:
            self.pool = SimpleConnectionPool(
                1, 20,
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "expenses_flow"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "")
            )
            print("✅ PostgreSQL Connected!")
            return True
        except Exception as e:
            print(f"❌ PostgreSQL Connection Failed: {e}")
            return False
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch_one:
                    return cur.fetchone()
                elif fetch_all:
                    return cur.fetchall()
                else:
                    conn.commit()
                    return None
        finally:
            self.pool.putconn(conn)

db = PostgresClient()