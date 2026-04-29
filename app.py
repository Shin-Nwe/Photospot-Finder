from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secretkey"

DB_DIR = os.path.join(app.root_path, "db")
DB_PATH = os.path.join(DB_DIR, "test.db")
SCHEMA_PATH = os.path.join(app.root_path, "schema.sql")
DEFAULT_SPOT_IMAGE = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80"

def init_db():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
            schema = schema_file.read()
            cursor.executescript(schema)

        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin123", "admin")
        )

        cursor.execute(
            "INSERT INTO spots (name, city, description) VALUES (?, ?, ?)",
            ("Shadowpeak Canyon", "Colorado, USA", "Beautiful canyon with amazing views.")
        )
        cursor.execute(
            "INSERT INTO spots (name, city, description) VALUES (?, ?, ?)",
            ("Crimson Rift", "Jordan", "Desert vibes and stunning landscape.")
        )

        conn.commit()
        conn.close()
        print("✅ Database initialized!")

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_spot(row):
    if not row:
        return None

    spot = dict(row)
    spot["location"] = spot.get("city", "Unknown location")
    spot["image"] = spot.get("image") or DEFAULT_SPOT_IMAGE
    spot["rating"] = spot.get("rating") if spot.get("rating") is not None else 0
    spot["comments"] = spot.get("comments", [])
    return spot

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            error = "Username and password are required."
        else:
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password, "user")
                )
                conn.commit()
                conn.close()
                return redirect("/login")
            except sqlite3.IntegrityError:
                conn.close()
                error = "That username is already taken."

    return render_template("register.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")

            return redirect("/spots")

        error = "Invalid username or password."

    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/spots")
def spots():
    conn = get_db()
    rows = conn.execute("SELECT * FROM spots").fetchall()
    conn.close()

    spots = [row_to_spot(row) for row in rows]
    return render_template("spots.html", spots=spots)

@app.route("/spot/<int:spot_id>")
def spot_detail(spot_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM spots WHERE id=?", (spot_id,)).fetchone()
    comments = conn.execute(
        "SELECT comment FROM comments WHERE spot_id=?",
        (spot_id,)
    ).fetchall()
    conn.close()

    if not row:
        return redirect("/spots")

    spot = row_to_spot(row)
    spot["comments"] = [comment["comment"] for comment in comments]
    return render_template("spot_detail.html", spot=spot)

@app.route("/add_spot", methods=["GET", "POST"])
def add_spot():
    if session.get("role") != "admin":
        return redirect("/spots")

    if request.method == "POST":
        name = request.form["name"]
        city = request.form["city"]
        description = request.form["description"]

        conn = get_db()
        conn.execute(
            "INSERT INTO spots (name, city, description) VALUES (?, ?, ?)",
            (name, city, description)
        )
        conn.commit()
        conn.close()

        return redirect("/spots")

    return render_template("add_spot.html")

@app.route("/delete_spot/<int:id>")
def delete_spot(id):
    if session.get("role") != "admin":
        return redirect("/spots")

    conn = get_db()
    conn.execute("DELETE FROM spots WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/spots")

@app.route("/add_comment/<int:spot_id>", methods=["POST"])
def add_comment(spot_id):
    if "user_id" not in session:
        return redirect("/login")

    comment = request.form["comment"]
    rating = request.form["rating"]

    conn = get_db()
    conn.execute(
        "INSERT INTO comments (comment, rating, user_id, spot_id) VALUES (?, ?, ?, ?)",
        (comment, rating, session["user_id"], spot_id)
    )
    conn.commit()
    conn.close()

    return redirect(f"/spot/{spot_id}")

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()
    spots = conn.execute("SELECT * FROM spots").fetchall()
    comments = conn.execute("""
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
    """).fetchall()
    conn.close()

    return render_template("dashboard.html", spots=spots, comments=comments)

@app.route("/delete_comment/<int:id>")
def delete_comment(id):
    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()
    conn.execute("DELETE FROM comments WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/profile")
def profile():
    user = {
        "username": session.get("username", "pixeluser"),
        "bio": session.get("bio", "Welcome to my profile ✨"),
        "photo": session.get("photo", "images/founder1.jpg")
    }

    spots = [
        {"name": "Photo 1"},
        {"name": "Photo 2"},
        {"name": "Photo 3"},
        {"name": "Photo 4"}
    ]

    return render_template("profile.html", user=user, spots=spots)

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    user = {
        "user_id": session.get("user_id", "001"),
        "username": session.get("username", "pixeluser"),
        "bio": session.get("bio", "Welcome to my profile ✨"),
        "photo": session.get("photo", "images/founder1.jpg")
    }

    if request.method == "POST":
        session["user_id"] = request.form.get("user_id")
        session["username"] = request.form.get("username")
        session["bio"] = request.form.get("bio")
        return redirect("/profile")

    return render_template("edit_profile.html", user=user)

@app.route("/search")
def search():
    query = request.args.get("query", "")
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM spots WHERE name LIKE ? OR city LIKE ?",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()

    spots = [row_to_spot(row) for row in rows]
    return render_template("spots.html", spots=spots)

if __name__ == "__main__":
    app.run(debug=True)