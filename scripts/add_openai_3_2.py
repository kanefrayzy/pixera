#!/usr/bin/env python
"""
Добавление модели OpenAI 3@2 (openai:3@2) в список видео-моделей.

- Категория: T2V (показывается в "Создать видео")
- Описание и порядок оформлены в стиле существующих карточек
- Макс. длительность: 8 сек (UI по умолчанию подскажет 4 сек)

Запуск:
  python scripts/add_openai_3_2.py
"""
import os
import sys
import django

# PYTHONPATH -> корень проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel

def main():
    data = {
        'name': 'OpenAI 3@2',
        'model_id': 'openai:3@2',
        'category': 't2v',
        'description': 'OpenAI 3@2: реалистичное T2V, рекомендуемая длительность 4 сек, 30 FPS.',
        'token_cost': 28,
        'max_duration': 8,
        'max_resolution': '1280x720',
        'is_active': True,
        'order': 7,
    }

    try:
        obj, created = VideoModel.objects.update_or_create(
            model_id=data['model_id'],
            defaults=data
        )
        if created:
            print(f"✓ Создана модель: {obj.name} ({obj.model_id})")
        else:
            print(f"↻ Обновлена модель: {obj.name} ({obj.model_id})")
    except Exception as e:
        print(f"Ошибка при добавлении/обновлении модели: {e}")
        raise

    print("\nАктуальные активные модели:")
    for m in VideoModel.objects.filter(is_active=True).order_by('category', 'order'):
        print(f"  {m.category.upper():4} | {m.model_id:16} | {m.name} (max_dur={m.max_duration})")

if __name__ == "__main__":
    main()
