from app.db import get_db
from app.services.members import require_librarian


def get_top_genres_borrowed(limit=15):
    """
    Returns ranking of top genres borrowed across all member loans.
    Includes borrow counts, active loans, total titles in genre, and share percentage.
    """
    db = get_db()
    
    total_borrows = db.execute("SELECT COUNT(*) FROM borrowing_record").fetchone()[0] or 0

    rows = db.execute(
        """
        SELECT 
            g.genre_id,
            g.name AS genre,
            g.slug,
            COUNT(b.borrowing_id) AS borrow_count,
            COUNT(CASE WHEN b.returned_at IS NULL AND b.borrowing_id IS NOT NULL THEN 1 END) AS active_loans,
            COUNT(DISTINCT mg.media_id) AS title_count
        FROM genre g
        JOIN media_genre mg ON mg.genre_id = g.genre_id
        LEFT JOIN media_copy c ON c.media_id = mg.media_id
        LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id
        GROUP BY g.genre_id
        ORDER BY borrow_count DESC, title_count DESC, g.name ASC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    results = []
    for rank, row in enumerate(rows, 1):
        count = row["borrow_count"]
        share = round((count / total_borrows) * 100, 1) if total_borrows > 0 else 0.0
        
        # Find top title in this genre
        top_title_row = db.execute(
            """
            SELECT m.title 
            FROM media_item m
            JOIN media_genre mg ON mg.media_id = m.media_id
            LEFT JOIN media_copy c ON c.media_id = m.media_id
            LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id
            WHERE mg.genre_id = ?
            GROUP BY m.media_id
            ORDER BY COUNT(b.borrowing_id) DESC, m.title ASC
            LIMIT 1
            """,
            (row["genre_id"],)
        ).fetchone()

        results.append({
            "rank": rank,
            "genre_id": row["genre_id"],
            "genre": row["genre"],
            "slug": row["slug"],
            "borrow_count": count,
            "active_loans": row["active_loans"],
            "title_count": row["title_count"],
            "share_percent": share,
            "top_title": top_title_row["title"] if top_title_row else "—",
        })

    return results


def get_top_book_types_borrowed():
    """
    Returns ranking and circulation breakdown across primary book types (categories):
    Manga, Comics, Graphic Novels, Novels, Literature, Magazines.
    """
    db = get_db()
    total_borrows = db.execute("SELECT COUNT(*) FROM borrowing_record").fetchone()[0] or 0

    rows = db.execute(
        """
        SELECT 
            m.category AS book_type,
            COUNT(DISTINCT m.media_id) AS total_titles,
            COUNT(DISTINCT c.copy_id) AS total_copies,
            COUNT(b.borrowing_id) AS borrow_count,
            COUNT(CASE WHEN b.returned_at IS NULL AND b.borrowing_id IS NOT NULL THEN 1 END) AS active_loans
        FROM media_item m
        LEFT JOIN media_copy c ON c.media_id = m.media_id
        LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id
        GROUP BY m.category
        ORDER BY borrow_count DESC, total_copies DESC, m.category ASC
        """
    ).fetchall()

    results = []
    for rank, row in enumerate(rows, 1):
        b_count = row["borrow_count"]
        copies = row["total_copies"]
        share = round((b_count / total_borrows) * 100, 1) if total_borrows > 0 else 0.0
        circ_rate = round(b_count / max(copies, 1), 2)

        results.append({
            "rank": rank,
            "book_type": row["book_type"],
            "borrow_count": b_count,
            "active_loans": row["active_loans"],
            "total_titles": row["total_titles"],
            "total_copies": copies,
            "circulation_rate": circ_rate,
            "share_percent": share,
        })
    return results


def get_book_borrowing_rankings(limit=50):
    """
    Returns full leaderboard rankings of individual books ordered by borrow frequency.
    Includes current inventory status, active loans, and genre tags.
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT 
            m.media_id,
            m.title,
            m.author,
            m.category,
            m.cover,
            COUNT(DISTINCT c.copy_id) AS copies,
            COUNT(DISTINCT CASE WHEN b.returned_at IS NULL AND b.borrowing_id IS NOT NULL THEN c.copy_id END) AS on_loan,
            COUNT(b.borrowing_id) AS borrow_count
        FROM media_item m
        LEFT JOIN media_copy c ON c.media_id = m.media_id
        LEFT JOIN borrowing_record b ON b.copy_id = c.copy_id
        GROUP BY m.media_id
        ORDER BY borrow_count DESC, m.title COLLATE NOCASE ASC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    # Pre-fetch all genre associations
    genres_rows = db.execute(
        """
        SELECT mg.media_id, g.name 
        FROM media_genre mg
        JOIN genre g ON g.genre_id = mg.genre_id
        ORDER BY g.name ASC
        """
    ).fetchall()
    genres_map = {}
    for r in genres_rows:
        genres_map.setdefault(r["media_id"], []).append(r["name"])

    results = []
    for rank, row in enumerate(rows, 1):
        available = max(0, row["copies"] - row["on_loan"])
        results.append({
            "rank": rank,
            "media_id": row["media_id"],
            "title": row["title"],
            "author": row["author"],
            "category": row["category"],
            "cover": row["cover"],
            "copies": row["copies"],
            "on_loan": row["on_loan"],
            "available": available,
            "borrow_count": row["borrow_count"],
            "genres": genres_map.get(row["media_id"], []),
            "is_popular": row["borrow_count"] >= 3,
        })
    return results


def get_analytics_summary():
    """Returns high-level KPI cards for the staff analytics header."""
    db = get_db()
    total_borrows = db.execute("SELECT COUNT(*) FROM borrowing_record").fetchone()[0] or 0
    active_loans = db.execute("SELECT COUNT(*) FROM borrowing_record WHERE returned_at IS NULL").fetchone()[0] or 0
    total_copies = db.execute("SELECT COUNT(*) FROM media_copy").fetchone()[0] or 0
    active_readers = db.execute("SELECT COUNT(DISTINCT member_id) FROM borrowing_record").fetchone()[0] or 0
    
    top_genres = get_top_genres_borrowed(limit=1)
    top_genre = top_genres[0]["genre"] if top_genres else "—"

    top_types = get_top_book_types_borrowed()
    top_type = top_types[0]["book_type"] if top_types else "—"

    top_books = get_book_borrowing_rankings(limit=1)
    top_book = top_books[0]["title"] if top_books else "—"

    return {
        "total_borrows": total_borrows,
        "active_loans": active_loans,
        "total_copies": total_copies,
        "active_readers": active_readers,
        "top_genre": top_genre,
        "top_type": top_type,
        "top_book": top_book,
    }
