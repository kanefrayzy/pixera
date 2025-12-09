#!/usr/bin/env python
"""
Добавление модели ByteDance 1.1 (bytedance:1@1) в список видео-моделей.

Требования:
- Должна быть доступна и в режимах Text-to-Video и Image-to-Video в UI.
  Из-за уникальности model_id в БД создаём одну запись с категорией "t2v".
  Во фронтенде она принудительно показывается и в i2v (см. static/js/video-generation.js).

Запуск:
  python scripts/add_bytedance_11.py
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
        'name': 'ByteDance 1.1',
        'model_id': 'bytedance:1@1',
        'category': 't2v',  # одна запись; во фронтенде показывается и в i2v
        'description': 'ByteDance 1.1: высокое качество, быстрый отклик. Доступна в T2V и I2V.',
        'token_cost': 32,
        'max_duration': 12,
        'max_resolution': '1920x1080',
        'is_active': True,
        'order': 5,
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
