Drop table if exists users;
Drop table if exists spots;
Drop table if exists comments;

CREATE TABLE users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
role TEXT
);

CREATE TABLE spots (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
city TEXT,
description TEXT,
image TEXT
);

CREATE TABLE comments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
comment TEXT,
rating INTEGER,
user_id INTEGER,
spot_id INTEGER,
FOREIGN KEY(user_id) REFERENCES users(id),
FOREIGN KEY(spot_id) REFERENCES spots(id)
);
