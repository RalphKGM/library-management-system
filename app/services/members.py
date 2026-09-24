import sqlite3
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db


def _required(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _public_member(row):
    return {key: row[key] for key in ("member_id", "full_name", "username", "registered_at")}


def register_member(full_name, username, password):
    full_name = _required(full_name, "full_name")
    username = _required(username, "username")
    password = _required(password, "password")
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO member (full_name, username, password_hash, registered_at) VALUES (?, ?, ?, ?)",
            (full_name, username, generate_password_hash(password, method="pbkdf2:sha256"), datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("username already exists") from exc
    return get_member(cursor.lastrowid)


def authenticate_member(username, password):
    username = _required(username, "username")
    if not isinstance(password, str):
        return None
    row = get_db().execute("SELECT * FROM member WHERE username = ?", (username,)).fetchone()
    return _public_member(row) if row and check_password_hash(row["password_hash"], password) else None


def get_member(member_id):
    row = get_db().execute("SELECT * FROM member WHERE member_id = ?", (member_id,)).fetchone()
    return _public_member(row) if row else None


def create_librarian(username, password):
    username = _required(username, "username")
    password = _required(password, "password")
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO librarian (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password, method="pbkdf2:sha256")),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("username already exists") from exc
    return {"librarian_id": cursor.lastrowid, "username": username}


def authenticate_librarian(username, password):
    username = _required(username, "username")
    if not isinstance(password, str):
        return None
    row = get_db().execute("SELECT * FROM librarian WHERE username = ?", (username,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return {"librarian_id": row["librarian_id"], "username": row["username"]}
    return None


def require_librarian(librarian_id):
    row = get_db().execute("SELECT librarian_id FROM librarian WHERE librarian_id = ?", (librarian_id,)).fetchone()
    if row is None:
        raise PermissionError("librarian account required")
