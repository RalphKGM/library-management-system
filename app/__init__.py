from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "library.sqlite3")
    )

    if test_config:
        app.config.update(test_config)

    from . import db
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api)
    from .ui import register_ui
    register_ui(app)
    return app
