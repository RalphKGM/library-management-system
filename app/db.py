import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

import click

from flask import current_app, g


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=15.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        g.db = db
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)
    columns = {row["name"] for row in get_db().execute("PRAGMA table_info(media_item)")}
    for name, declaration in (
        ("description", "TEXT NOT NULL DEFAULT ''"),
        ("cover", "TEXT NOT NULL DEFAULT 'catalog-placeholder.svg'"),
        ("added_at", "TEXT NOT NULL DEFAULT ''"),
        ("source_key", "TEXT"),
    ):
        if name not in columns:
            get_db().execute(f"ALTER TABLE media_item ADD COLUMN {name} {declaration}")
    get_db().execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_media_source_key ON media_item(source_key) WHERE source_key IS NOT NULL")
    get_db().commit()
    ensure_books_have_genres(offline_only=True)

    # Automatically ensure default accounts and demo catalog exist if empty
    try:
        staff_count = get_db().execute("SELECT COUNT(*) FROM librarian").fetchone()[0]
        book_count = get_db().execute("SELECT COUNT(*) FROM media_item").fetchone()[0]
        if staff_count == 0 or book_count < 10:
            seed_demo_dataset()
    except Exception:
        pass


def ensure_books_have_genres(offline_only=True):
    db = get_db()
    unassigned = db.execute(
        "SELECT m.media_id, m.title, m.author, m.category, m.description "
        "FROM media_item m WHERE NOT EXISTS (SELECT 1 FROM media_genre mg WHERE mg.media_id = m.media_id)"
    ).fetchall()
    if not unassigned:
        return
    from app.services.google_books import draft_genre_tags_for_book
    from app.services.media import set_media_genres
    for item in unassigned:
        tags = draft_genre_tags_for_book(
            item["title"], item["author"], item["category"], item["description"],
            offline_only=offline_only,
        )
        set_media_genres(item["media_id"], tags)


def seed_demo_dataset(password="DemoReader2026!"):
    db = get_db()
    # 1. Ensure staff account exists
    staff = db.execute("SELECT librarian_id, username FROM librarian ORDER BY librarian_id LIMIT 1").fetchone()
    if staff is None:
        from app.services.members import create_librarian
        try:
            staff = create_librarian("demo_staff", "DemoStaff2026!")
        except Exception:
            staff = db.execute("SELECT librarian_id, username FROM librarian ORDER BY librarian_id LIMIT 1").fetchone()
    
    if staff is None:
        return 0, 0, 0

    from app.sample_catalog import CATEGORIES
    from app.services.media import add_copies, add_media
    from app.services.members import register_member

    dataset_path = Path(__file__).parent / "data" / "demo_open_library.json"
    if not dataset_path.exists():
        return 0, 0, 0

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    candidates = dataset.get("books", [])
    existing_keys = {
        row["source_key"] for row in db.execute(
            "SELECT source_key FROM media_item WHERE source_key IS NOT NULL"
        )
    }
    stock_levels = (1, 4, 2, 7, 0, 3, 6, 2, 5, 8)
    added_books = 0
    added_copies = 0
    for category_index, category in enumerate(CATEGORIES):
        current = db.execute(
            "SELECT COUNT(*) FROM media_item WHERE category = ?", (category,)
        ).fetchone()[0]
        needed = max(0, 10 - current)
        available = [
            book for book in candidates
            if book["category"] == category and book["source_key"] not in existing_keys
        ]
        for index, book in enumerate(available[:needed]):
            work = add_media({
                "title": book["title"], "author": book["author"],
                "category": category, "cover": book["cover"],
                "source_key": book["source_key"],
            }, staff["librarian_id"])
            stock = stock_levels[(category_index * 2 + index) % len(stock_levels)]
            if stock:
                add_copies(work["media_id"], stock, staff["librarian_id"])
            existing_keys.add(book["source_key"])
            added_books += 1
            added_copies += stock

    names = (
        "Alex Rivera", "Sam Santos", "Jamie Cruz", "Taylor Reyes", "Morgan Lim",
        "Casey Navarro", "Riley Tan", "Jordan Garcia", "Avery Mendoza", "Drew Flores",
    )
    added_members = 0
    for index, name in enumerate(names, 1):
        username = f"demo_reader_{index:02d}"
        if db.execute("SELECT 1 FROM member WHERE username = ?", (username,)).fetchone():
            continue
        try:
            register_member(name, username, password)
            added_members += 1
        except Exception:
            pass

    loan_count = db.execute("SELECT COUNT(*) FROM borrowing_record").fetchone()[0]
    if loan_count < 10:
        member_rows = db.execute("SELECT member_id FROM member ORDER BY member_id").fetchall()
        copy_rows = db.execute("SELECT copy_id FROM media_copy ORDER BY copy_id").fetchall()
        if member_rows and copy_rows:
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            for i in range(min(24, len(copy_rows))):
                m_id = member_rows[i % len(member_rows)]["member_id"]
                c_id = copy_rows[i]["copy_id"]
                b_time = (now - timedelta(days=30 - i)).isoformat()
                r_time = None if i < 8 else (now - timedelta(days=max(1, 30 - i - 7))).isoformat()
                try:
                    db.execute(
                        "INSERT INTO borrowing_record (member_id, copy_id, borrowed_at, returned_at) VALUES (?, ?, ?, ?)",
                        (m_id, c_id, b_time, r_time),
                    )
                except sqlite3.IntegrityError:
                    pass
            db.commit()

    ensure_books_have_genres()
    return added_books, added_copies, added_members


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized and verified.")

    @app.cli.command("create-librarian")
    @click.option("--username", prompt=True)
    @click.password_option()
    def create_librarian_command(username, password):
        from app.services.members import create_librarian

        init_db()
        try:
            create_librarian(username, password)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo("Librarian account created.")

    @app.cli.command("seed-sample")
    def seed_sample_command():
        from app.sample_catalog import SAMPLE_WORKS

        init_db()
        db = get_db()
        if db.execute("SELECT 1 FROM media_item LIMIT 1").fetchone():
            raise click.ClickException("Catalog already contains titles. Sample titles were not added.")
        for work in SAMPLE_WORKS:
            cursor = db.execute(
                "INSERT INTO media_item (title, author, category, volume, progress_unit, total_units, description, cover, added_at) "
                "VALUES (?, ?, ?, ?, 'page', ?, ?, ?, ?)",
                (work["title"], work["author"], work["category"], work["volume"],
                 int(work["length"].split()[0]), work["description"], work["cover"],
                 datetime.now(timezone.utc).isoformat()),
            )
            for number in range(work["copies"]):
                db.execute(
                    "INSERT INTO media_copy (media_id, accession_number) VALUES (?, ?)",
                    (cursor.lastrowid, f"SAMPLE-{work['slug'].upper()}-{number + 1:02d}"),
                )
        db.commit()
        click.echo("Sample catalog added.")

    @app.cli.command("seed-demo")
    @click.option("--password", default="DemoReader2026!", show_default=True)
    def seed_demo_command(password):
        init_db()
        added_books, added_copies, added_members = seed_demo_dataset(password=password)
        click.echo(
            f"Added {added_books} Open Library books, {added_copies} copies, "
            f"and {added_members} demo members."
        )
        click.echo("Demo member usernames: demo_reader_01 through demo_reader_10")
        click.echo(f"Demo member password: {password}")
