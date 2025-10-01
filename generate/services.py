# FILE: generate/services.py
"""
Опциональный модуль. Если здесь нет run_generation_sync,
views.py сам подставит фолбэк. Рекомендуется оставить как есть.
"""
import base64
from datetime import datetime
from django.core.files.base import ContentFile
from django.db.models.fields.files import FileField

_PNG_1x1 = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
)

def _first_filefield_name(job) -> str | None:
    for name in ("result", "output", "image", "file"):
        f = getattr(job, name, None)
        if f is not None and hasattr(f, "save"):
            return name
    for field in job._meta.fields:
        if isinstance(field, FileField):
            f = getattr(job, field.name, None)
            if f is not None and hasattr(f, "save"):
                return field.name
    return None

def run_generation_sync(job) -> None:
    """Реализация по умолчанию (можете заменить своей логикой генерации)."""
    if hasattr(job, "status"):
        job.status = "RUNNING"
    if hasattr(job, "progress"):
        job.progress = 10
    job.save()

    if hasattr(job, "progress"):
        job.progress = 90
        job.save(update_fields=["progress"])

    name = _first_filefield_name(job)
    if name:
        filename = f"job_{job.pk}_{int(datetime.now().timestamp())}.png"
        getattr(job, name).save(filename, ContentFile(_PNG_1x1), save=True)

    if hasattr(job, "progress"):
        job.progress = 100
    if hasattr(job, "status"):
        job.status = "DONE"
    job.save()
