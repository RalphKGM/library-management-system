from pathlib import Path
import os
import secrets

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    secret_file = Path(app.instance_path) / "session.key"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    if not secret_file.exists():
        try:
            descriptor = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(secrets.token_hex(32))
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "library.sqlite3"),
        SECRET_KEY=os.environ.get("LIBRARY_SECRET_KEY") or secret_file.read_text().strip(),
    )

    if test_config:
        app.config.update(test_config)

    from . import db
    db.init_app(app)

    from .security import init_security
    init_security(app)

    from .routes import api
    app.register_blueprint(api)
    from .ui import register_ui
    register_ui(app)
    return app
