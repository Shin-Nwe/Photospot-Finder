import sqlite3
from db import get_db

def init_db():
    db = get_db()
    
    with open("db/schema.sql", "r") as f:
        db.executescript(f.read())
    
    db.commit()
    db.close()
    print("✅ Database created successfully!")

if __name__ == "__main__":
    init_db()