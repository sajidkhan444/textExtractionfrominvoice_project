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
                database=os.getenv("DB_NAME", "expense_flow"),
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
                print(f"🔍 [DEBUG] Executing SQL: {query[:200]}...")
                if params:
                    # Truncate long params for display
                    params_display = []
                    for p in params:
                        if isinstance(p, str) and len(p) > 100:
                            params_display.append(f"{p[:100]}...")
                        else:
                            params_display.append(p)
                    print(f"🔍 [DEBUG] Params: {params_display}")
                
                cur.execute(query, params)
                
                # Handle different query types
                if fetch_one:
                    result = cur.fetchone()
                    conn.commit()  # CRITICAL: Commit after fetch
                    print(f"🔍 [DEBUG] fetch_one result: {result}")
                    return result
                elif fetch_all:
                    result = cur.fetchall()
                    conn.commit()  # CRITICAL: Commit after fetch
                    print(f"🔍 [DEBUG] fetch_all returned {len(result) if result else 0} rows")
                    return result
                else:
                    conn.commit()  # Commit for INSERT/UPDATE/DELETE without RETURNING
                    print(f"🔍 [DEBUG] Query committed successfully")
                    return None
                    
        except Exception as e:
            print(f"❌ [DEBUG] Database error: {e}")
            print(f"❌ [DEBUG] Failed query: {query}")
            if params:
                print(f"❌ [DEBUG] Failed params: {params}")
            conn.rollback()
            raise e
        finally:
            self.pool.putconn(conn)


# Create a global instance
db = PostgresClient()