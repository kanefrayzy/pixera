# FILE: ai_gallery/asgi.py
"""
ASGI config for ai_gallery project.
Exposes the ASGI callable as a module-level variable named `application`.
Docs: https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from pathlib import Path

from django.core.asgi import get_asgi_application

# ── Load .env early (so DJANGO_SETTINGS_MODULE and others can come from env) ──
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

if load_dotenv:
    base_dir = Path(__file__).resolve().parent.parent
    env_file = base_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file.as_posix())

# ── Default settings module (can be overridden by environment) ──
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "ai_gallery.settings"))

# ── Create ASGI application ──
application = get_asgi_application()
