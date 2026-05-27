from __future__ import annotations

import pytest

from taxgpt import create_app
from taxgpt.models import db


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "ENABLE_CSRF": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite3'}",
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "OLLAMA_BASE_URL": "http://ollama.invalid:11434",
            "AUTO_INIT_DB": True,
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_and_login(client, email: str = "ada@example.com", password: str = "password123"):
    return client.post(
        "/register",
        data={"display_name": "Ada", "email": email, "password": password},
        follow_redirects=True,
    )
