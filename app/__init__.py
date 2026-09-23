from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True, static_folder=None)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-in-production",
        DATABASE=str(Path(app.instance_path) / "library.sqlite3")
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from . import db
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api)
    return app
