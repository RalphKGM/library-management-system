import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

import click

from flask import current_app, g


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
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


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

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
        from app.sample_catalog import CATEGORIES
        from app.services.media import add_copies, add_media
        from app.services.members import register_member

        init_db()
        db = get_db()
        staff = db.execute("SELECT librarian_id FROM librarian ORDER BY librarian_id LIMIT 1").fetchone()
        if staff is None:
            raise click.ClickException("Create a librarian account before loading demo data.")
        dataset_path = Path(__file__).parent / "data" / "demo_open_library.json"
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        candidates = dataset["books"]
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
            if len(available) < needed:
                raise click.ClickException(f"Not enough Open Library books for {category}.")
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
            register_member(name, username, password)
            added_members += 1
        click.echo(
            f"Added {added_books} Open Library books, {added_copies} copies, "
            f"and {added_members} demo members."
        )
        click.echo("Demo member usernames: demo_reader_01 through demo_reader_10")
        click.echo(f"Demo member password: {password}")
