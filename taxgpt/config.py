from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'taxgpt.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.163:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "minicpm-v:latest")
    OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "90"))
    ENABLE_CSRF = os.environ.get("ENABLE_CSRF", "true").lower() not in {"0", "false", "no"}
