# -*- coding: utf-8 -*-
"""config.py — Environment-driven configuration. Reads from .env if present
(via python-dotenv if installed; silently skipped otherwise so the app
still runs with plain environment variables / defaults)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    PORT = int(os.environ.get("PORT", 5000))
    HOST = os.environ.get("HOST", "0.0.0.0")
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 300))
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    JSON_SORT_KEYS = False
    REBUILD_DB_ON_START = os.environ.get("REBUILD_DB_ON_START", "0") == "1"
