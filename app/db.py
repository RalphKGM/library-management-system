import sqlite3
from pathlib import Path
import click
from flask import current_app, g


def get_db():
    """Open a request-scoped SQLite connection with foreign keys enabled."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(error=None):
    """Close the request connection during Flask teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the instance directory and apply schema.sql explicitly."""
    db_path = Path(current_app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Clear the existing data and create new tables."""
        init_db()
        click.echo("Initialized the database.")
