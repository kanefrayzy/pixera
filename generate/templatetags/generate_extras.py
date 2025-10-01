# generate/templatetags/generate_extras.py
from django import template
from django.templatetags.static import static
from django.db.models.fields.files import FileField

register = template.Library()

PREFERRED_FIELDS = ("result", "output", "image", "file")

@register.filter
def job_thumb_url(job):
    """
    Возвращает URL любого файла-результата у джоба.
    1) пробуем популярные имена полей,
    2) затем проходим по всем FileField,
    3) иначе — плейсхолдер.
    """
    # 1) привычные имена
    for name in PREFERRED_FIELDS:
        f = getattr(job, name, None)
        url = getattr(f, "url", None)
        if url:
            return url

    # 2) любые FileField
    for field in getattr(job, "_meta").fields:
        if isinstance(field, FileField):
            f = getattr(job, field.name, None)
            url = getattr(f, "url", None)
            if url:
                return url

    # 3) плейсхолдер (положите файл в static/img/placeholder.png)
    return static("img/placeholder.png")
