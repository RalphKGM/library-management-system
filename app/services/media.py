import re
import sqlite3
from uuid import uuid4
from datetime import datetime, timezone

from app.db import get_db
from app.services.members import require_librarian


FIELDS = ("title", "author", "category", "volume", "progress_unit", "total_units", "description", "cover", "source_key")


def _validate(details):
    if not isinstance(details, dict):
        raise ValueError("media details must be a dictionary")
    if set(details) - set(FIELDS):
        raise ValueError("unknown media field")
    for name in ("title", "author", "category"):
        if name in details and (not isinstance(details[name], str) or not details[name].strip()):
            raise ValueError(f"{name} is required")
        if name in details:
            details[name] = details[name].strip()
    if "progress_unit" in details and details["progress_unit"] not in ("page", "chapter"):
        raise ValueError("progress_unit must be page or chapter")
    if "total_units" in details and details["total_units"] is not None:
        if type(details["total_units"]) is not int or details["total_units"] <= 0:
            raise ValueError("total_units must be positive")
    if "volume" in details and details["volume"] is not None and not isinstance(details["volume"], str):
        raise ValueError("volume must be text")
    if "description" in details and (not isinstance(details["description"], str) or len(details["description"]) > 2000):
        raise ValueError("description must be at most 2000 characters")
    if "cover" in details and details["cover"] not in _cover_options() and not re.fullmatch(r"https://covers\.openlibrary\.org/b/id/[1-9][0-9]*-M\.jpg", str(details["cover"])):
        raise ValueError("invalid cover image")
    if "source_key" in details and details["source_key"] is not None and not re.fullmatch(r"/works/OL[0-9]+W", str(details["source_key"])):
        raise ValueError("invalid Open Library work")
    return details


def _cover_options():
    from pathlib import Path

    return {path.name for path in (Path(__file__).resolve().parents[1] / "static/images/covers").glob("*.svg")}


def add_media(details, librarian_id):
    require_librarian(librarian_id)
    data = _validate(dict(details))
    for field in ("title", "author", "category"):
        if field not in data:
            raise ValueError(f"{field} is required")
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO media_item (title, author, category, volume, progress_unit, total_units, description, cover, added_at, source_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data["title"], data["author"], data["category"], data.get("volume"), data.get("progress_unit", "page"), data.get("total_units"), data.get("description", ""), data.get("cover", "catalog-placeholder.svg"), datetime.now(timezone.utc).isoformat(), data.get("source_key")),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("this Open Library title is already in the catalog") from exc
    return dict(db.execute("SELECT * FROM media_item WHERE media_id = ?", (cursor.lastrowid,)).fetchone())


def update_media(media_id, changes, librarian_id):
    require_librarian(librarian_id)
    data = _validate(dict(changes))
    if not data:
        raise ValueError("no changes supplied")
    if "source_key" in data:
        raise ValueError("Open Library source cannot be changed")
    db = get_db()
    if not db.execute("SELECT 1 FROM media_item WHERE media_id = ?", (media_id,)).fetchone():
        return None
    if data.get("total_units") is not None:
        highest = db.execute(
            "SELECT MAX(position) FROM ("
            "SELECT current_position AS position FROM reading_progress WHERE media_id = ? "
            "UNION ALL SELECT position FROM bookmark WHERE media_id = ?)",
            (media_id, media_id),
        ).fetchone()[0]
        if highest is not None and data["total_units"] < highest:
            raise ValueError("total units cannot be below saved reading positions")
    columns = ", ".join(f"{key} = ?" for key in data)
    db.execute(f"UPDATE media_item SET {columns} WHERE media_id = ?", (*data.values(), media_id))
    db.commit()
    return dict(db.execute("SELECT * FROM media_item WHERE media_id = ?", (media_id,)).fetchone())


def search_media(query="", category=None):
    if not isinstance(query, str) or (category is not None and not isinstance(category, str)):
        raise ValueError("search terms must be text")
    sql = "SELECT * FROM media_item WHERE (title LIKE ? OR author LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    if category is not None:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY title, media_id"
    return [dict(row) for row in get_db().execute(sql, params)]


def add_copy(media_id, accession_number, librarian_id):
    require_librarian(librarian_id)
    if not isinstance(accession_number, str) or not accession_number.strip():
        raise ValueError("accession_number is required")
    db = get_db()
    if not db.execute("SELECT 1 FROM media_item WHERE media_id = ?", (media_id,)).fetchone():
        raise ValueError("media item does not exist")
    try:
        cursor = db.execute("INSERT INTO media_copy (media_id, accession_number) VALUES (?, ?)", (media_id, accession_number.strip()))
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("accession number already exists") from exc
    return dict(db.execute("SELECT * FROM media_copy WHERE copy_id = ?", (cursor.lastrowid,)).fetchone())


def add_copies(media_id, count, librarian_id):
    require_librarian(librarian_id)
    if type(count) is not int or not 1 <= count <= 500:
        raise ValueError("quantity must be between 1 and 500")
    db = get_db()
    if not db.execute("SELECT 1 FROM media_item WHERE media_id = ?", (media_id,)).fetchone():
        raise ValueError("media item does not exist")
    try:
        for _ in range(count):
            cursor = db.execute(
                "INSERT INTO media_copy (media_id, accession_number) VALUES (?, ?)",
                (media_id, f"AUTO-{uuid4().hex}"),
            )
            db.execute(
                "UPDATE media_copy SET accession_number = ? WHERE copy_id = ?",
                (f"LIB-{cursor.lastrowid:06d}", cursor.lastrowid),
            )
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise ValueError("could not generate a unique copy ID") from exc
    return count


def get_available_copies(media_id):
    rows = get_db().execute(
        "SELECT c.* FROM media_copy c WHERE c.media_id = ? AND NOT EXISTS "
        "(SELECT 1 FROM borrowing_record b WHERE b.copy_id = c.copy_id AND b.returned_at IS NULL) "
        "ORDER BY c.copy_id", (media_id,),
    )
    return [dict(row) for row in rows]
