# blog/utils.py
import re
from django.utils.text import slugify


def transliterate_slug(value):
    """
    Создает slug с транслитерацией кириллицы.
    """
    if not value:
        return "post"

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
        slug = "post"

    return slug[:180]  # Ограничиваем длину для базы slug
