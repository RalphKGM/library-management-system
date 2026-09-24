from datetime import datetime, timezone

from app.db import get_db


STATUSES = ("not_started", "reading", "completed")


def _validate_position(member_id, media_id, position):
    if type(position) is not int or position < 0:
        raise ValueError("position must be a nonnegative whole number")
    db = get_db()
    if not db.execute("SELECT 1 FROM member WHERE member_id = ?", (member_id,)).fetchone():
        raise ValueError("member does not exist")
    media = db.execute("SELECT total_units FROM media_item WHERE media_id = ?", (media_id,)).fetchone()
    if media is None:
        raise ValueError("title does not exist")
    if media["total_units"] is not None and position > media["total_units"]:
        raise ValueError("position exceeds the title length")


def update_progress(member_id, media_id, position, status):
    _validate_position(member_id, media_id, position)
    if status not in STATUSES:
        raise ValueError("invalid reading status")
    db = get_db()
    db.execute(
        "INSERT INTO reading_progress (member_id, media_id, current_position, status, updated_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(member_id, media_id) DO UPDATE SET "
        "current_position = excluded.current_position, status = excluded.status, updated_at = excluded.updated_at",
        (member_id, media_id, position, status, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return get_progress(member_id, media_id)


def get_progress(member_id, media_id):
    row = get_db().execute(
        "SELECT * FROM reading_progress WHERE member_id = ? AND media_id = ?",
        (member_id, media_id),
    ).fetchone()
    return dict(row) if row else None


def get_all_progress(member_id):
    rows = get_db().execute(
        "SELECT p.*, m.title, m.author, m.category, m.total_units, m.cover FROM reading_progress p "
        "JOIN media_item m ON m.media_id = p.media_id WHERE p.member_id = ? "
        "ORDER BY p.updated_at DESC",
        (member_id,),
    )
    return [dict(row) for row in rows]


def add_bookmark(member_id, media_id, position, note=""):
    _validate_position(member_id, media_id, position)
    if not isinstance(note, str) or len(note) > 500:
        raise ValueError("note must be at most 500 characters")
    db = get_db()
    cursor = db.execute(
        "INSERT INTO bookmark (member_id, media_id, position, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (member_id, media_id, position, note.strip(), datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM bookmark WHERE bookmark_id = ?", (cursor.lastrowid,)).fetchone())


def get_bookmarks(member_id, media_id=None):
    sql = (
        "SELECT b.*, m.title, m.author, m.category, m.cover FROM bookmark b "
        "JOIN media_item m ON m.media_id = b.media_id WHERE b.member_id = ?"
    )
    params = [member_id]
    if media_id is not None:
        sql += " AND b.media_id = ?"
        params.append(media_id)
    sql += " ORDER BY b.created_at DESC, b.bookmark_id DESC"
    return [dict(row) for row in get_db().execute(sql, params)]


def remove_bookmark(member_id, bookmark_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM bookmark WHERE bookmark_id = ? AND member_id = ?",
        (bookmark_id, member_id),
    )
    db.commit()
    return cursor.rowcount == 1
