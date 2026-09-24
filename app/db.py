import sqlite3
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
    ):
        if name not in columns:
            get_db().execute(f"ALTER TABLE media_item ADD COLUMN {name} {declaration}")
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
