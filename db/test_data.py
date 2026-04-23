from db import get_db

def insert_data():
    db = get_db()
    cursor = db.cursor()

    # Insert admin
    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'admin')
    """)

    # Insert normal user
    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES ('user', 'user123', 'user')
    """)

    # Insert spots
    spots = [
        ("Sunset Hill", "Sheffield", "Best sunset photography spot", "https://via.placeholder.com/400"),
        ("Peak District", "Sheffield", "Amazing nature views", "https://via.placeholder.com/400"),
        ("London Bridge", "London", "Famous photo location", "https://via.placeholder.com/400")
    ]

    for spot in spots:
        cursor.execute("""
            INSERT INTO spots (name, city, description, image_url)
            VALUES (?, ?, ?, ?)
        """, spot)

    db.commit()
    db.close()
    print("✅ Test data added!")

if __name__ == "__main__":
    insert_data()