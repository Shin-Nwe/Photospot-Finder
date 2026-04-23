from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        conn.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)",
            (username, password, "user")
        )
        conn.commit()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")

            return redirect("/spots")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- VIEW SPOTS ----------------
@app.route("/spots")
def spots():

    conn = get_db()

    spots = conn.execute("SELECT * FROM spots").fetchall()

    return render_template("spots.html", spots=spots)


# ---------------- ADD SPOT (ADMIN ONLY) ----------------
@app.route("/add_spot", methods=["GET","POST"])
def add_spot():

    if session.get("role") != "admin":
        return redirect("/spots")

    if request.method == "POST":
        name = request.form["name"]
        city = request.form["city"]
        description = request.form["description"]

        conn = get_db()
        conn.execute(
            "INSERT INTO spots (name,city,description) VALUES (?,?,?)",
            (name, city, description)
        )
        conn.commit()

        return redirect("/spots")

    return render_template("add_spot.html")


# ---------------- DELETE SPOT (ADMIN) ----------------
@app.route("/delete_spot/<int:id>")
def delete_spot(id):

    if session.get("role") != "admin":
        return redirect("/spots")

    conn = get_db()

    conn.execute("DELETE FROM spots WHERE id=?", (id,))
    conn.commit()

    return redirect("/spots")


# ---------------- ADD COMMENT ----------------
@app.route("/add_comment/<int:spot_id>", methods=["POST"])
def add_comment(spot_id):

    if "user_id" not in session:
        return redirect("/login")

    comment = request.form["comment"]
    rating = request.form["rating"]

    conn = get_db()

    conn.execute(
        "INSERT INTO comments (comment,rating,user_id,spot_id) VALUES (?,?,?,?)",
        (comment, rating, session["user_id"], spot_id)
    )

    conn.commit()

    return redirect("/spots")


# ---------------- ADMIN DASHBOARD ----------------
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

    return render_template("dashboard.html", spots=spots, comments=comments)


# ---------------- DELETE COMMENT ----------------
@app.route("/delete_comment/<int:id>")
def delete_comment(id):

    if session.get("role") != "admin":
        return redirect("/")

    conn = get_db()

    conn.execute("DELETE FROM comments WHERE id=?", (id,))
    conn.commit()

    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)


@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    return render_template("profile.html", user=user)

@app.route("/search")
def search():

    query = request.args.get("query")

    conn = get_db()

    spots = conn.execute(
        "SELECT * FROM spots WHERE name LIKE ? OR city LIKE ?",
        (f"%{query}%", f"%{query}%")
    ).fetchall()

    return render_template("spots.html", spots=spots)

@app.route('/profile/<username>')
def profile(username):
    user = get_user(username)
    photos = get_user_photos(username)
    return render_template('profile.html', user=user, photos=photos)