# generate/templatetags/generate_extras.py
from django import template
from django.templatetags.static import static
from django.db.models.fields.files import FileField
from django.utils.text import slugify
import re

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


@register.filter
def safe_slugify(value):
    """
    Безопасная slugification с поддержкой кириллицы.
    Если обычный slugify возвращает пустую строку, используем fallback.
    """
    if not value:
        return "untitled"

    # Попробуем обычный slugify
    slug = slugify(value)

    # Если пустой (кириллица), используем transliteration
    if not slug:
        # Простая транслитерация основных кириллических символов
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            ' ': '-', '_': '-'
        }

        # Приводим к нижнему регистру и транслитерируем
        text = value.lower()
        transliterated = ''
        for char in text:
            transliterated += translit_map.get(char, char)

        # Удаляем недопустимые символы и создаем slug
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '', transliterated)
        slug = re.sub(r'[-_]+', '-', slug)  # Убираем повторяющиеся дефисы
        slug = slug.strip('-')  # Убираем дефисы в начале и конце

        # Если всё равно пустой, используем fallback
        if not slug:
            slug = "untitled"

    # Ограничиваем длину
    return slug[:50] if slug else "untitled"
