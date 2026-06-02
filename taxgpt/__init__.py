from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from sqlalchemy import inspect, text

from .config import Config
from .models import db
from .views import bp as web_bp

__version__ = "1.2.0"


def create_app(config: object | dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.register_blueprint(web_bp)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create database tables."""
        with app.app_context():
            _initialise_database()
        print("Initialized the database.")

    @app.context_processor
    def inject_version() -> dict[str, str]:
        return {"app_version": __version__}

    if app.config.get("AUTO_INIT_DB", True):
        with app.app_context():
            _initialise_database()

    return app


def _initialise_database() -> None:
    db.create_all()
    _ensure_tax_entries_document_line_id()


def _ensure_tax_entries_document_line_id() -> None:
    inspector = inspect(db.engine)
    if not inspector.has_table("tax_entries"):
        return

    columns = {column["name"] for column in inspector.get_columns("tax_entries")}
    if "document_line_id" in columns:
        return

    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE tax_entries ADD COLUMN document_line_id VARCHAR(80) NOT NULL DEFAULT ''"))
