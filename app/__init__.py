from pathlib import Path
import os
import secrets

from flask import Flask, url_for


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    secret_key = os.environ.get("LIBRARY_SECRET_KEY")
    if not secret_key:
        secret_file = Path(app.instance_path) / "session.key"
        try:
            secret_file.parent.mkdir(parents=True, exist_ok=True)
            if secret_file.exists():
                secret_key = secret_file.read_text(encoding="utf-8").strip()
            if not secret_key:
                secret_key = secrets.token_hex(32)
                try:
                    secret_file.write_text(secret_key, encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            secret_key = "the-reading-room-session-fallback-secret-2026"

    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "library.sqlite3"),
        SECRET_KEY=secret_key or secrets.token_hex(32),
    )

    if test_config:
        app.config.update(test_config)

    @app.template_filter("cover_src")
    def cover_src(cover):
        if isinstance(cover, str) and cover.startswith("https://covers.openlibrary.org/b/id/"):
            return cover
        return url_for("static", filename="images/covers/" + cover)

    from . import db
    db.init_app(app)
    with app.app_context():
        db.init_db()

    from .security import init_security
    init_security(app)

    from .routes import api
    app.register_blueprint(api)
    from .ui import register_ui
    register_ui(app)
    return app
