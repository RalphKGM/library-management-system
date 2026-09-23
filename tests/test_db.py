import sqlite3
import pytest
from app.db import get_db, init_db


def test_get_close_db(app):
    with app.app_context():
        db = get_db()
        assert db is get_db()

    with pytest.raises(sqlite3.ProgrammingError) as exc_info:
        db.execute("SELECT 1")

    assert "closed" in str(exc_info.value).lower()


def test_foreign_keys_enabled(app):
    with app.app_context():
        db = get_db()
        cursor = db.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1


def test_tables_created(app):
    with app.app_context():
        db = get_db()
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "member" in table_names
        assert "media_item" in table_names
        assert "media_copy" in table_names
        assert "borrowing_record" in table_names
        assert "reading_progress" in table_names
        assert "bookmark" in table_names


def test_init_db_command(runner, monkeypatch):
    class Recorder:
        called = False

    def fake_init_db():
        Recorder.called = True

    monkeypatch.setattr("app.db.init_db", fake_init_db)
    result = runner.invoke(args=["init-db"])
    assert "Initialized the database." in result.output
    assert Recorder.called is True
