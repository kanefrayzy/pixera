#!/usr/bin/env python
"""
Скрипт для добавления примера видео в showcase
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import ShowcaseVideo

def add_video_example():
    """Добавляет один сжатый пример видео"""

    # Проверяем, есть ли уже примеры
    if ShowcaseVideo.objects.exists():
        print("✓ Примеры видео уже существуют")
        return

    # Создаём один пример с placeholder видео (без категории)
    example = ShowcaseVideo.objects.create(
        title="Cinematic Portrait",
        prompt="cinematic portrait, soft studio light, 85mm lens, shallow depth of field, warm color grading, professional photography",
        video_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        is_active=True,
        order=0
    )

    print(f"✓ Создан пример видео: {example.title}")
    print(f"  ID: {example.id}")
    print(f"  Промпт: {example.prompt}")
    print(f"  URL: {example.video_url}")

if __name__ == '__main__':
    print("Добавление примера видео в showcase...")
    add_video_example()
    print("\n✅ Готово!")
