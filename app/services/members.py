from datetime import datetime, timezone
import sqlite3
from typing import Optional
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db
from ..models import Member


def _row_to_member(row: sqlite3.Row) -> Member:
    """Helper to convert a sqlite3.Row to a Member dataclass instance."""
    return Member(
        member_id=row["member_id"],
        full_name=row["full_name"],
        username=row["username"],
        password_hash=row["password_hash"],
        registered_at=row["registered_at"],
        role=row["role"] if "role" in row.keys() else "member",
    )


def register_member(full_name: str, username: str, password: str, role: str = "member") -> Member:
    """Validate details, hash the password, and save a member.
    
    Raises:
        ValueError: If fields are missing, invalid, or username already exists.
    """
    if not full_name or not full_name.strip():
        raise ValueError("Full name cannot be empty.")
    if not username or not username.strip():
        raise ValueError("Username cannot be empty.")
    if not password:
        raise ValueError("Password cannot be empty.")

    clean_full_name = full_name.strip()
    clean_username = username.strip()

    valid_roles = ("member", "librarian")
    if role not in valid_roles:
        raise ValueError(f"Invalid role '{role}'. Allowed roles are: {', '.join(valid_roles)}.")

    password_hash = generate_password_hash(password)
    registered_at = datetime.now(timezone.utc).isoformat()

    db = get_db()
    try:
        cursor = db.execute(
            """
            INSERT INTO member (full_name, username, password_hash, role, registered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_full_name, clean_username, password_hash, role, registered_at),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        db.rollback()
        raise ValueError(f"Username '{clean_username}' is already taken.") from e

    return Member(
        member_id=cursor.lastrowid,
        full_name=clean_full_name,
        username=clean_username,
        password_hash=password_hash,
        registered_at=registered_at,
        role=role,
    )


def authenticate_member(username: str, password: str) -> Optional[Member]:
    """Check credentials without exposing password hashes.
    
    Returns:
        Member if authentication succeeds, None otherwise.
    """
    if not username or not password:
        return None

    db = get_db()
    row = db.execute(
        "SELECT * FROM member WHERE username = ?",
        (username.strip(),),
    ).fetchone()

    if row is None:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return _row_to_member(row)


def get_member(member_id: int) -> Optional[Member]:
    """Retrieve a registered member by ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM member WHERE member_id = ?",
        (member_id,),
    ).fetchone()

    if row is None:
        return None

    return _row_to_member(row)


def get_member_by_username(username: str) -> Optional[Member]:
    """Retrieve a registered member by username."""
    if not username:
        return None

    db = get_db()
    row = db.execute(
        "SELECT * FROM member WHERE username = ?",
        (username.strip(),),
    ).fetchone()

    if row is None:
        return None

    return _row_to_member(row)


def is_librarian(member: Optional[Member]) -> bool:
    """Return True if the member has librarian permissions, otherwise False."""
    return bool(member and getattr(member, "role", None) == "librarian")
