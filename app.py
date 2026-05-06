from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "secretkey"

DB_DIR = os.path.join(app.root_path, "db")
DB_PATH = os.path.join(DB_DIR, "test.db")
SCHEMA_PATH = os.path.join(app.root_path, "schema.sql")

PROFILE_UPLOAD_FOLDER = os.path.join("static", "images", "profiles")
SPOT_UPLOAD_FOLDER = os.path.join("static", "images", "spots")

app.config["PROFILE_UPLOAD_FOLDER"] = PROFILE_UPLOAD_FOLDER
app.config["SPOT_UPLOAD_FOLDER"] = SPOT_UPLOAD_FOLDER


@app.context_processor
def inject_site_name():
    return {"siteName": "Pixel Trial"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(SPOT_UPLOAD_FOLDER, exist_ok=True)

    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())

        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin@example.com", "admin123", "admin")
        )

        cursor.execute(
            "INSERT INTO profiles (user_id, bio, profile_photo, instagram) VALUES (?, ?, ?, ?)",
            (1, "Admin profile", "default.jpg", "")
        )

        conn.commit()
        conn.close()
        print("Database initialized")


init_db()


@app.route('/')
def index():
    db = get_db()
    popular = db.execute('''
        SELECT
            spots.id,
            spots.name,
            spots.location,
            spots.cover_image,
            users.username,
            users.id AS user_id,
            ROUND(AVG(ratings.rating), 1) AS avg_rating,
            COUNT(DISTINCT likes.id)      AS like_count
        FROM spots
        JOIN users ON users.id = spots.user_id
        LEFT JOIN ratings ON ratings.spot_id = spots.id
        LEFT JOIN likes   ON likes.spot_id   = spots.id
        GROUP BY spots.id
        HAVING avg_rating IS NOT NULL
        ORDER BY avg_rating DESC
        LIMIT 6
    ''').fetchall()

    return render_template('index.html', popular=popular)

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip() or None

        if not username or not password:
            error = "Username and password are required."
        else:
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                    (username, email, password, "user")
                )
                user_id = cur.lastrowid

                db.execute(
                    "INSERT INTO profiles (user_id, bio, profile_photo, instagram) VALUES (?, ?, ?, ?)",
                    (user_id, "", "default.jpg", "")
                )

                db.commit()
                return redirect("/login")

            except sqlite3.IntegrityError:
                error = "Username or email already exists."
            finally:
                db.close()

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/feed")

        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/feed")
@app.route("/spots")
def feed():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    posts = db.execute("""
        SELECT
            spots.id,
            spots.name,
            spots.location,
            spots.description,
            spots.cover_image,
            spots.created_at,
            users.id AS user_id,
            users.username,
            profiles.profile_photo,
            COALESCE(l.like_count, 0) AS like_count,
            COALESCE(c.comment_count, 0) AS comment_count,
            COALESCE(r.avg_rating, 0) AS avg_rating
        FROM spots
        JOIN users ON users.id = spots.user_id
        LEFT JOIN profiles ON profiles.user_id = spots.user_id
        LEFT JOIN (
            SELECT spot_id, COUNT(*) AS like_count
            FROM likes
            GROUP BY spot_id
        ) l ON l.spot_id = spots.id
        LEFT JOIN (
            SELECT spot_id, COUNT(*) AS comment_count
            FROM comments
            GROUP BY spot_id
        ) c ON c.spot_id = spots.id
        LEFT JOIN (
            SELECT spot_id, ROUND(AVG(rating), 1) AS avg_rating
            FROM ratings
            GROUP BY spot_id
        ) r ON r.spot_id = spots.id
        ORDER BY spots.created_at DESC
    """).fetchall()

    liked_rows = db.execute(
        "SELECT spot_id FROM likes WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    liked_ids = {row["spot_id"] for row in liked_rows}

    db.close()

    return render_template("feed.html", posts=posts, liked_ids=liked_ids)



@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute(
        'SELECT id, username, email FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()
    return render_template('settings.html', user=user)


@app.route('/settings/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current  = request.form.get('current_password', '')
    new_pw   = request.form.get('new_password', '')
    confirm  = request.form.get('confirm_password', '')

    db   = get_db()
    user = db.execute(
        'SELECT password FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()

    if not check_password_hash(user['password'], current):
        flash('Current password is incorrect.', 'pw')
        return redirect(url_for('settings') + '#password')

    if len(new_pw) < 6:
        flash('New password must be at least 6 characters.', 'pw')
        return redirect(url_for('settings') + '#password')

    if new_pw != confirm:
        flash('New passwords do not match.', 'pw')
        return redirect(url_for('settings') + '#password')

    db.execute(
        'UPDATE users SET password = ? WHERE id = ?',
        (generate_password_hash(new_pw), session['user_id'])
    )
    db.commit()
    flash('Password updated successfully.', 'pw_ok')
    return redirect(url_for('settings') + '#password')


@app.route('/settings/change_email', methods=['POST'])
def change_email():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    new_email = request.form.get('new_email', '').strip()
    password  = request.form.get('email_password', '')

    if not new_email:
        flash('Please enter a new email.', 'email')
        return redirect(url_for('settings') + '#email')

    db   = get_db()
    user = db.execute(
        'SELECT password FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()

    if not check_password_hash(user['password'], password):
        flash('Password is incorrect.', 'email')
        return redirect(url_for('settings') + '#email')

    existing = db.execute(
        'SELECT id FROM users WHERE email = ? AND id != ?',
        (new_email, session['user_id'])
    ).fetchone()
    if existing:
        flash('That email is already in use.', 'email')
        return redirect(url_for('settings') + '#email')

    db.execute(
        'UPDATE users SET email = ? WHERE id = ?',
        (new_email, session['user_id'])
    )
    db.commit()
    flash('Email updated successfully.', 'email_ok')
    return redirect(url_for('settings') + '#email')


@app.route('/settings/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    password = request.form.get('delete_password', '')
    db   = get_db()
    user = db.execute(
        'SELECT password FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()

    if not check_password_hash(user['password'], password):
        flash('Password is incorrect.', 'delete')
        return redirect(url_for('settings') + '#delete')

    uid = session['user_id']
    # Delete in child-first order
    db.execute('DELETE FROM followers WHERE follower_id=? OR following_id=?', (uid, uid))
    db.execute('DELETE FROM likes     WHERE user_id=?', (uid,))
    db.execute('DELETE FROM ratings   WHERE user_id=?', (uid,))
    db.execute('DELETE FROM comments  WHERE user_id=?', (uid,))
    db.execute('DELETE FROM spot_images WHERE spot_id IN (SELECT id FROM spots WHERE user_id=?)', (uid,))
    db.execute('DELETE FROM spots     WHERE user_id=?', (uid,))
    db.execute('DELETE FROM profiles  WHERE user_id=?', (uid,))
    db.execute('DELETE FROM users     WHERE id=?',      (uid,))
    db.commit()

    session.clear()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))



@app.route("/add-post", methods=["GET", "POST"])
def add_post():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()
        rating = request.form.get("rating")
        files = request.files.getlist("photos")[:6]

        if not name:
            return render_template("add_post.html", error="Title is required.")

        db = get_db()

        cur = db.execute("""
            INSERT INTO spots (user_id, name, location, description)
            VALUES (?, ?, ?, ?)
        """, (session["user_id"], name, location, description))

        spot_id = cur.lastrowid
        cover_filename = None

        for i, file in enumerate(files):
            if file and file.filename:
                filename = secure_filename(file.filename)
                filename = f"{spot_id}_{i}_{filename}"

                save_path = os.path.join(app.config["SPOT_UPLOAD_FOLDER"], filename)
                file.save(save_path)

                if i == 0:
                    cover_filename = filename

                db.execute("""
                    INSERT INTO spot_images (spot_id, filename, sort_order)
                    VALUES (?, ?, ?)
                """, (spot_id, filename, i))

        if cover_filename:
            db.execute(
                "UPDATE spots SET cover_image = ? WHERE id = ?",
                (cover_filename, spot_id)
            )

        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    db.execute("""
                        INSERT INTO ratings (user_id, spot_id, rating)
                        VALUES (?, ?, ?)
                    """, (session["user_id"], spot_id, rating))
            except ValueError:
                pass

        db.commit()
        db.close()

        return redirect("/feed")

    return render_template("add_post.html")


@app.route("/spot/<int:spot_id>")
def spot_detail(spot_id):
    db = get_db()

    spot = db.execute("""
        SELECT
            spots.*,
            users.id AS user_id,
            users.username,
            profiles.profile_photo,
            profiles.bio,
            COALESCE(l.like_count, 0) AS like_count,
            COALESCE(r.avg_rating, 0) AS avg_rating
        FROM spots
        JOIN users ON users.id = spots.user_id
        LEFT JOIN profiles ON profiles.user_id = spots.user_id
        LEFT JOIN (
            SELECT spot_id, COUNT(*) AS like_count
            FROM likes
            GROUP BY spot_id
        ) l ON l.spot_id = spots.id
        LEFT JOIN (
            SELECT spot_id, ROUND(AVG(rating), 1) AS avg_rating
            FROM ratings
            GROUP BY spot_id
        ) r ON r.spot_id = spots.id
        WHERE spots.id = ?
    """, (spot_id,)).fetchone()

    if not spot:
        db.close()
        return "Post not found", 404

    images = db.execute("""
        SELECT filename
        FROM spot_images
        WHERE spot_id = ?
        ORDER BY sort_order
    """, (spot_id,)).fetchall()

    comments = db.execute("""
        SELECT comments.*, users.username, profiles.profile_photo
        FROM comments
        JOIN users ON users.id = comments.user_id
        LEFT JOIN profiles ON profiles.user_id = comments.user_id
        WHERE comments.spot_id = ?
        ORDER BY comments.created_at ASC
    """, (spot_id,)).fetchall()

    user_liked = False
    user_rating = None

    if "user_id" in session:
        user_liked = db.execute(
            "SELECT 1 FROM likes WHERE user_id = ? AND spot_id = ?",
            (session["user_id"], spot_id)
        ).fetchone() is not None

        rating_row = db.execute(
            "SELECT rating FROM ratings WHERE user_id = ? AND spot_id = ?",
            (session["user_id"], spot_id)
        ).fetchone()

        user_rating = rating_row["rating"] if rating_row else None

    db.close()

    return render_template(
        "spot_detail.html",
        spot=spot,
        images=images,
        comments=comments,
        user_liked=user_liked,
        user_rating=user_rating
    )


@app.route('/like/<int:spot_id>', methods=['POST'])
def like(spot_id):
    if 'user_id' not in session:
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('login'))
    
    db = get_db()
    existing = db.execute(
        'SELECT 1 FROM likes WHERE user_id = ? AND spot_id = ?',
        (session['user_id'], spot_id)
    ).fetchone()
    
    if existing:
        db.execute('DELETE FROM likes WHERE user_id = ? AND spot_id = ?',
                   (session['user_id'], spot_id))
        liked = False
    else:
        db.execute('INSERT INTO likes (user_id, spot_id) VALUES (?, ?)',
                   (session['user_id'], spot_id))
        liked = True
    
    # Get updated like count
    like_count = db.execute(
        'SELECT COUNT(*) FROM likes WHERE spot_id = ?',
        (spot_id,)
    ).fetchone()[0]
    
    db.commit()
    
    # Check if this is an AJAX request
    if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'liked': liked,
            'like_count': like_count
        })
    
    # Check referrer to determine where to redirect
    referrer = request.referrer
    if referrer and f'/spot/{spot_id}' in referrer:
        # Came from spot detail page, redirect back there
        return redirect(url_for('spot_detail', spot_id=spot_id))
    else:
        # Came from feed or other page, redirect to feed
        return redirect(url_for('feed') + f'#post-{spot_id}')


@app.route("/comment/<int:spot_id>", methods=["POST"])
def add_comment(spot_id):
    if "user_id" not in session:
        return redirect("/login")

    comment = request.form.get("comment", "").strip()

    if comment:
        db = get_db()
        db.execute(
            "INSERT INTO comments (user_id, spot_id, comment) VALUES (?, ?, ?)",
            (session["user_id"], spot_id, comment)
        )
        db.commit()
        db.close()

    return redirect(f"/spot/{spot_id}#comments")


@app.route("/delete-comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    
    # Check if comment exists and belongs to current user
    comment = db.execute(
        "SELECT spot_id FROM comments WHERE id = ? AND user_id = ?",
        (comment_id, session["user_id"])
    ).fetchone()
    
    if comment:
        # Delete the comment
        db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        db.commit()
        spot_id = comment["spot_id"]
    else:
        # Comment not found or doesn't belong to user
        spot_id = None
    
    db.close()
    
    if spot_id:
        return redirect(f"/spot/{spot_id}#comments")
    else:
        return redirect("/feed")


@app.route("/rate/<int:spot_id>", methods=["POST"])
def rate(spot_id):
    if "user_id" not in session:
        return redirect("/login")

    rating = request.form.get("rating")

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return redirect(f"/spot/{spot_id}")

    if 1 <= rating <= 5:
        db = get_db()
        db.execute("""
            INSERT INTO ratings (user_id, spot_id, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, spot_id)
            DO UPDATE SET rating = excluded.rating
        """, (session["user_id"], spot_id, rating))
        db.commit()
        db.close()

    return redirect(f"/spot/{spot_id}")


@app.route("/profile")
@app.route("/profile/<int:user_id>")
def profile(user_id=None):
    if "user_id" not in session:
        return redirect("/login")

    if user_id is None:
        user_id = session["user_id"]

    db = get_db()

    user = db.execute("""
        SELECT
            users.id,
            users.username,
            profiles.bio,
            profiles.profile_photo,
            profiles.instagram
        FROM users
        LEFT JOIN profiles ON users.id = profiles.user_id
        WHERE users.id = ?
    """, (user_id,)).fetchone()

    if not user:
        db.close()
        return "User not found", 404

    posts = db.execute("""
        SELECT *
        FROM spots
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    followers = db.execute(
        "SELECT COUNT(*) FROM followers WHERE following_id = ?",
        (user_id,)
    ).fetchone()[0]

    following = db.execute(
        "SELECT COUNT(*) FROM followers WHERE follower_id = ?",
        (user_id,)
    ).fetchone()[0]

    likes = db.execute("""
        SELECT COUNT(*)
        FROM likes
        JOIN spots ON likes.spot_id = spots.id
        WHERE spots.user_id = ?
    """, (user_id,)).fetchone()[0]

    avg_rating = db.execute("""
        SELECT ROUND(AVG(rating), 1)
        FROM ratings
        JOIN spots ON ratings.spot_id = spots.id
        WHERE spots.user_id = ?
    """, (user_id,)).fetchone()[0]

    if avg_rating is None:
        avg_rating = 0

    is_following = False
    if session["user_id"] != user_id:
        is_following = db.execute(
            "SELECT 1 FROM followers WHERE follower_id = ? AND following_id = ?",
            (session["user_id"], user_id)
        ).fetchone() is not None

    db.close()

    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        followers=followers,
        following=following,
        likes=likes,
        avg_rating=avg_rating,
        is_following=is_following
    )


@app.route("/follow/<int:user_id>", methods=["POST"])
def follow(user_id):
    if "user_id" not in session:
        return redirect("/login")

    follower_id = session["user_id"]

    if follower_id == user_id:
        return redirect(f"/profile/{user_id}")

    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM followers WHERE follower_id = ? AND following_id = ?",
        (follower_id, user_id)
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM followers WHERE follower_id = ? AND following_id = ?",
            (follower_id, user_id)
        )
    else:
        db.execute(
            "INSERT INTO followers (follower_id, following_id) VALUES (?, ?)",
            (follower_id, user_id)
        )

    db.commit()
    db.close()

    return redirect(f"/profile/{user_id}")


@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    db = get_db()

    if request.method == "POST":
        bio = request.form.get("bio", "").strip()
        instagram = request.form.get("instagram", "").strip()
        file = request.files.get("profile_photo")

        filename = None

        if file and file.filename:
            filename = secure_filename(file.filename)
            filename = f"user_{user_id}_{filename}"

            save_path = os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], filename)
            file.save(save_path)

        existing = db.execute(
            "SELECT * FROM profiles WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if existing:
            if filename:
                db.execute("""
                    UPDATE profiles
                    SET bio = ?, instagram = ?, profile_photo = ?
                    WHERE user_id = ?
                """, (bio, instagram, filename, user_id))
            else:
                db.execute("""
                    UPDATE profiles
                    SET bio = ?, instagram = ?
                    WHERE user_id = ?
                """, (bio, instagram, user_id))
        else:
            db.execute("""
                INSERT INTO profiles (user_id, bio, instagram, profile_photo)
                VALUES (?, ?, ?, ?)
            """, (user_id, bio, instagram, filename or "default.jpg"))

        db.commit()
        db.close()

        return redirect("/profile")

    user = db.execute("""
        SELECT
            users.id,
            users.username,
            profiles.bio,
            profiles.profile_photo,
            profiles.instagram
        FROM users
        LEFT JOIN profiles ON users.id = profiles.user_id
        WHERE users.id = ?
    """, (user_id,)).fetchone()

    db.close()

    return render_template("edit_profile.html", user=user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    # 🔒 Get post (only owner can edit)
    post = db.execute("""
        SELECT * FROM spots
        WHERE id = ? AND user_id = ?
    """, (post_id, session["user_id"])).fetchone()

    if not post:
        db.close()
        return "Post not found", 404

    # 📸 Get images
    images = db.execute("""
        SELECT * FROM spot_images
        WHERE spot_id = ?
        ORDER BY sort_order
    """, (post_id,)).fetchall()

    # ⭐ Get current rating
    r = db.execute("""
        SELECT rating FROM ratings
        WHERE user_id = ? AND spot_id = ?
    """, (session["user_id"], post_id)).fetchone()

    current_rating = r["rating"] if r else None

    if request.method == "POST":

        name = request.form.get("name")
        location = request.form.get("location")
        description = request.form.get("description")
        rating = request.form.get("rating")

        # 🗑 DELETE selected images
        delete_ids = request.form.getlist("delete_image")

        for img_id in delete_ids:
            img = db.execute(
                "SELECT filename FROM spot_images WHERE id = ?",
                (img_id,)
            ).fetchone()

            if img:
                # delete file from folder
                path = os.path.join(app.config["SPOT_UPLOAD_FOLDER"], img["filename"])
                if os.path.exists(path):
                    os.remove(path)

                # delete from DB
                db.execute("DELETE FROM spot_images WHERE id = ?", (img_id,))

        # ➕ ADD new images
        files = request.files.getlist("photos")

        # count remaining images
        current_count = db.execute(
            "SELECT COUNT(*) FROM spot_images WHERE spot_id = ?",
            (post_id,)
        ).fetchone()[0]

        for i, file in enumerate(files):
            if file and file.filename and current_count < 6:
                filename = secure_filename(file.filename)
                filename = f"{post_id}_{current_count}_{filename}"

                save_path = os.path.join(app.config["SPOT_UPLOAD_FOLDER"], filename)
                file.save(save_path)

                db.execute("""
                    INSERT INTO spot_images (spot_id, filename, sort_order)
                    VALUES (?, ?, ?)
                """, (post_id, filename, current_count))

                current_count += 1

        # 🧠 UPDATE post info
        db.execute("""
            UPDATE spots
            SET name = ?, location = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (name, location, description, post_id, session["user_id"]))

        # ⭐ UPDATE rating
        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    db.execute("""
                        INSERT INTO ratings (user_id, spot_id, rating)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id, spot_id)
                        DO UPDATE SET rating = excluded.rating
                    """, (session["user_id"], post_id, rating))
            except:
                pass

        # 🖼 UPDATE cover image (first image)
        first_img = db.execute("""
            SELECT filename FROM spot_images
            WHERE spot_id = ?
            ORDER BY sort_order ASC
            LIMIT 1
        """, (post_id,)).fetchone()

        if first_img:
            db.execute("""
                UPDATE spots
                SET cover_image = ?
                WHERE id = ?
            """, (first_img["filename"], post_id))
        else:
            db.execute("""
                UPDATE spots
                SET cover_image = NULL
                WHERE id = ?
            """, (post_id,))

        db.commit()
        db.close()

        return redirect(url_for("spot_detail", spot_id=post_id))

    db.close()

    return render_template(
        "edit_post.html",
        post=post,
        images=images,
        current_rating=current_rating
    )



@app.route("/delete-post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    db.execute("DELETE FROM likes WHERE spot_id = ?", (post_id,))
    db.execute("DELETE FROM ratings WHERE spot_id = ?", (post_id,))
    db.execute("DELETE FROM comments WHERE spot_id = ?", (post_id,))
    db.execute("DELETE FROM spot_images WHERE spot_id = ?", (post_id,))

    db.execute("""
        DELETE FROM spots
        WHERE id = ? AND user_id = ?
    """, (post_id, session["user_id"]))

    db.commit()
    db.close()

    return redirect("/profile")


@app.route("/search")
def search():
    if "user_id" not in session:
        return redirect("/login")

    query = request.args.get("query", "")

    db = get_db()

    posts = db.execute("""
        SELECT
            spots.id,
            spots.name,
            spots.location,
            spots.description,
            spots.cover_image,
            spots.created_at,
            users.id AS user_id,
            users.username,
            profiles.profile_photo,
            COALESCE(l.like_count, 0) AS like_count,
            COALESCE(c.comment_count, 0) AS comment_count,
            COALESCE(r.avg_rating, 0) AS avg_rating
        FROM spots
        JOIN users ON users.id = spots.user_id
        LEFT JOIN profiles ON profiles.user_id = spots.user_id
        LEFT JOIN (
            SELECT spot_id, COUNT(*) AS like_count
            FROM likes
            GROUP BY spot_id
        ) l ON l.spot_id = spots.id
        LEFT JOIN (
            SELECT spot_id, COUNT(*) AS comment_count
            FROM comments
            GROUP BY spot_id
        ) c ON c.spot_id = spots.id
        LEFT JOIN (
            SELECT spot_id, ROUND(AVG(rating), 1) AS avg_rating
            FROM ratings
            GROUP BY spot_id
        ) r ON r.spot_id = spots.id
        WHERE spots.name LIKE ? OR spots.location LIKE ?
        ORDER BY spots.created_at DESC
    """, (f"%{query}%", f"%{query}%")).fetchall()

    liked_rows = db.execute(
        "SELECT spot_id FROM likes WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    liked_ids = {row["spot_id"] for row in liked_rows}

    db.close()

    return render_template("feed.html", posts=posts, liked_ids=liked_ids)


if __name__ == "__main__":
    app.run(debug=True)