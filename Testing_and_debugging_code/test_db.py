import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="expenses_flow",
        user="postgres",
        password="1234"  # Replace with actual password
    )
    print("✅ Connected to expenses_flow database!")
    
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM invoices;")
    count = cur.fetchone()
    print(f"📊 Total invoices: {count[0]}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")