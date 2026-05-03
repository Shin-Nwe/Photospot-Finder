-- DROP OLD TABLES (order matters — children first)
DROP TABLE IF EXISTS followers;
DROP TABLE IF EXISTS likes;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS spot_images;
DROP TABLE IF EXISTS spots;
DROP TABLE IF EXISTS profiles;
DROP TABLE IF EXISTS users;

-- USERS
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE,
    password    TEXT NOT NULL,
    role        TEXT DEFAULT 'user'
);

-- PROFILES
CREATE TABLE profiles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER UNIQUE NOT NULL,
    bio           TEXT,
    profile_photo TEXT DEFAULT 'default.jpg',
    instagram     TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- SPOTS (posts)
CREATE TABLE spots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    name        TEXT NOT NULL,
    location    TEXT,
    description TEXT,
    cover_image TEXT,                          -- first/hero image filename
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- SPOT IMAGES (multiple photos per post)
CREATE TABLE spot_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_id    INTEGER NOT NULL,
    filename   TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY(spot_id) REFERENCES spots(id)
);

-- COMMENTS
CREATE TABLE comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    spot_id    INTEGER NOT NULL,
    comment    TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(spot_id) REFERENCES spots(id)
);

-- RATINGS (owner rates their own post, or visitors rate spots)
CREATE TABLE ratings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    spot_id    INTEGER NOT NULL,
    rating     INTEGER CHECK(rating >= 1 AND rating <= 5),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(spot_id) REFERENCES spots(id),
    UNIQUE(user_id, spot_id)
);

-- LIKES
CREATE TABLE likes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    spot_id    INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(spot_id) REFERENCES spots(id),
    UNIQUE(user_id, spot_id)
);

-- FOLLOWERS
CREATE TABLE followers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id  INTEGER NOT NULL,
    following_id INTEGER NOT NULL,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(follower_id)  REFERENCES users(id),
    FOREIGN KEY(following_id) REFERENCES users(id),
    UNIQUE(follower_id, following_id)
);