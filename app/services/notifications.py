from datetime import datetime, timezone

from app.db import get_db


def add_notification(db, role, recipient_id, message, target):
    db.execute(
        "INSERT INTO notification (recipient_role, recipient_id, message, target, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (role, recipient_id, message, target, datetime.now(timezone.utc).isoformat()),
    )


def notify_librarians(db, message):
    for row in db.execute("SELECT librarian_id FROM librarian"):
        add_notification(db, "librarian", row["librarian_id"], message, "/librarian/loans")


def inbox(role, recipient_id, limit=100):
    return get_db().execute(
        "SELECT * FROM notification WHERE recipient_role = ? AND recipient_id = ? "
        "ORDER BY notification_id DESC LIMIT ?",
        (role, recipient_id, limit),
    ).fetchall()


def unread_count(role, recipient_id):
    return get_db().execute(
        "SELECT COUNT(*) FROM notification WHERE recipient_role = ? AND recipient_id = ? "
        "AND read_at IS NULL",
        (role, recipient_id),
    ).fetchone()[0]


def mark_read(role, recipient_id, notification_id=None):
    db = get_db()
    when = datetime.now(timezone.utc).isoformat()
    if notification_id is None:
        db.execute(
            "UPDATE notification SET read_at = ? WHERE recipient_role = ? "
            "AND recipient_id = ? AND read_at IS NULL",
            (when, role, recipient_id),
        )
    else:
        db.execute(
            "UPDATE notification SET read_at = ? WHERE notification_id = ? "
            "AND recipient_role = ? AND recipient_id = ? AND read_at IS NULL",
            (when, notification_id, role, recipient_id),
        )
    db.commit()


def clear_all(role, recipient_id):
    db = get_db()
    db.execute(
        "DELETE FROM notification WHERE recipient_role = ? AND recipient_id = ?",
        (role, recipient_id),
    )
    db.commit()
