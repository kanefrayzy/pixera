# FILE: ai_gallery/wsgi.py
"""
WSGI config for ai_gallery project.
Exposes the WSGI callable as a module-level variable named `application`.
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# ── Load .env early (so DJANGO_SETTINGS_MODULE and others can come from env) ──
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # dotenv is optional in production
    load_dotenv = None

if load_dotenv:
    # Load project-level .env (if present)
    base_dir = Path(__file__).resolve().parent.parent
    env_file = base_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file.as_posix())

# ── Default settings module (can be overridden by environment) ──
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "ai_gallery.settings"))

# ── Create WSGI application ──
application = get_wsgi_application()
