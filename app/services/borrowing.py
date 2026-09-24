import sqlite3
from datetime import datetime, timezone

from app.db import get_db


def borrow_copy(member_id, copy_id):
    db = get_db()
    if not db.execute("SELECT 1 FROM member WHERE member_id = ?", (member_id,)).fetchone():
        raise ValueError("member does not exist")
    if not db.execute("SELECT 1 FROM media_copy WHERE copy_id = ?", (copy_id,)).fetchone():
        raise ValueError("copy does not exist")
    if db.execute(
        "SELECT 1 FROM borrowing_record b "
        "JOIN media_copy borrowed ON borrowed.copy_id = b.copy_id "
        "JOIN media_copy chosen ON chosen.media_id = borrowed.media_id "
        "WHERE b.member_id = ? AND chosen.copy_id = ? AND b.returned_at IS NULL",
        (member_id, copy_id),
    ).fetchone():
        raise ValueError("you already have this title borrowed")
    try:
        cursor = db.execute(
            "INSERT INTO borrowing_record (member_id, copy_id, borrowed_at) "
            "SELECT ?, ?, ? WHERE NOT EXISTS "
            "(SELECT 1 FROM borrowing_record WHERE copy_id = ? AND returned_at IS NULL)",
            (member_id, copy_id, datetime.now(timezone.utc).isoformat(), copy_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("copy is already borrowed")
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise ValueError("copy is already borrowed") from exc
    return dict(db.execute("SELECT * FROM borrowing_record WHERE borrowing_id = ?", (cursor.lastrowid,)).fetchone())


def return_copy(borrowing_id):
    db = get_db()
    cursor = db.execute(
        "UPDATE borrowing_record SET returned_at = ? WHERE borrowing_id = ? AND returned_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), borrowing_id),
    )
    if cursor.rowcount != 1:
        raise ValueError("active borrowing not found")
    db.commit()
    return dict(db.execute("SELECT * FROM borrowing_record WHERE borrowing_id = ?", (borrowing_id,)).fetchone())


def get_borrowing_history(member_id):
    rows = get_db().execute(
        "SELECT b.*, c.media_id, m.title, m.author, m.category, m.cover "
        "FROM borrowing_record b JOIN media_copy c ON c.copy_id = b.copy_id "
        "JOIN media_item m ON m.media_id = c.media_id "
        "WHERE b.member_id = ? ORDER BY b.borrowed_at DESC, b.borrowing_id DESC",
        (member_id,),
    )
    return [dict(row) for row in rows]
