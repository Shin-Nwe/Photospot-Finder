import sqlite3
import os

def init_db():
    """Initialize the database with the schema"""
    
    # Create db directory if it doesn't exist
    db_dir = "db"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    db_path = os.path.join(db_dir, "test.db")
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open("schema.sql", "r") as schema_file:
        schema = schema_file.read()
        cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized successfully at {db_path}")

if __name__ == "__main__":
    init_db()