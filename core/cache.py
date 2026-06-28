# -*- coding: utf-8 -*-
"""
core/cache.py — Tiny in-memory TTL cache for read-heavy GET endpoints.

Every aggregate query already hits an indexed SQLite table (fast), but
the dashboard re-requests the same handful of (endpoint, country)
combinations constantly as users flip tabs — caching those responses for
a short TTL cuts DB load to ~nothing without needing Redis for what is,
in this app, a single-process deployment.

Not thread-safe-hardened beyond a basic lock — fine for the gunicorn
--workers=1 / Flask dev server deployment this project targets. For a
multi-process deployment, swap this for Flask-Caching + Redis (noted in
README "Scaling Further").
"""
import threading
import time
from functools import wraps

from flask import request

_store = {}
_lock = threading.Lock()
DEFAULT_TTL = 300  # seconds


def cached(fn=None, *, ttl: int = DEFAULT_TTL):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__module__}.{f.__name__}:{request.full_path}"
            now = time.time()
            with _lock:
                hit = _store.get(key)
                if hit and hit[1] > now:
                    return hit[0]
            result = f(*args, **kwargs)
            with _lock:
                _store[key] = (result, now + ttl)
            return result
        return wrapper

    return decorator(fn) if fn is not None else decorator


def clear() -> int:
    with _lock:
        n = len(_store)
        _store.clear()
    return n


def stats() -> dict:
    with _lock:
        return {"entries": len(_store)}
