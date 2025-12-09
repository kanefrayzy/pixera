#!/usr/bin/env python
"""
Скрипт для создания категорий и примеров видео для I2V и T2V режимов
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoPromptCategory, ShowcaseVideo
from django.contrib.auth import get_user_model

User = get_user_model()

def create_video_categories():
    """Создание категорий для I2V и T2V"""

    print("🎬 Создание категорий для видео...")

    # I2V категории
    i2v_categories = [
        {
            'name': 'Портреты',
            'slug': 'i2v-portraits',
            'description': 'Оживление портретных фотографий с естественными движениями',
            'mode': 'i2v',
            'order': 0
        },
        {
            'name': 'Пейзажи',
            'slug': 'i2v-landscapes',
            'description': 'Анимация природных и городских пейзажей',
            'mode': 'i2v',
            'order': 1
        }
    ]

    # T2V категории
    t2v_categories = [
        {
            'name': 'Кинематограф',
            'slug': 't2v-cinematic',
            'description': 'Кинематографические сцены и эффекты',
            'mode': 't2v',
            'order': 0
        },
        {
            'name': 'Природа',
            'slug': 't2v-nature',
            'description': 'Природные явления и пейзажи',
            'mode': 't2v',
            'order': 1
        }
    ]

    created_count = 0

    for cat_data in i2v_categories + t2v_categories:
        cat, created = VideoPromptCategory.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        if created:
            print(f"  ✓ Создана категория: {cat.name} ({cat.mode})")
            created_count += 1
        else:
            print(f"  - Категория уже существует: {cat.name}")

    print(f"\n✅ Создано категорий: {created_count}")
    return created_count

def create_showcase_videos():
    """Создание примеров видео для showcase"""

    print("\n🎥 Создание примеров видео...")

    # Получаем или создаем пользователя
    try:
        user = User.objects.filter(is_staff=True).first()
        if not user:
            user = User.objects.first()
    except:
        user = None

    # I2V примеры
    i2v_examples = [
        {
            'title': 'Animated Portrait',
            'prompt': 'animate this portrait with subtle facial movements, natural breathing, gentle eye blinks',
            'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
            'mode': 'i2v',
            'order': 0
        }
    ]

    # T2V примеры
    t2v_examples = [
        {
            'title': 'Cinematic Sunset',
            'prompt': 'cinematic sunset over ocean, camera slowly panning, warm golden hour lighting, 4k quality',
            'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            'mode': 't2v',
            'order': 0
        }
    ]

    created_count = 0

    for video_data in i2v_examples + t2v_examples:
        # Проверяем, существует ли уже
        exists = ShowcaseVideo.objects.filter(
            title=video_data['title'],
            mode=video_data['mode']
        ).exists()

        if not exists:
            video_data['is_active'] = True
            if user:
                video_data['uploaded_by'] = user

            video = ShowcaseVideo.objects.create(**video_data)
            print(f"  ✓ Создан пример: {video.title} ({video.mode})")
            created_count += 1
        else:
            print(f"  - Пример уже существует: {video_data['title']}")

    print(f"\n✅ Создано примеров: {created_count}")
    return created_count

def main():
    print("=" * 60)
    print("SETUP VIDEO CONTENT - Создание категорий и примеров")
    print("=" * 60)

    try:
        cat_count = create_video_categories()
        vid_count = create_showcase_videos()

        print("\n" + "=" * 60)
        print("✅ ГОТОВО!")
        print(f"   Категорий создано: {cat_count}")
        print(f"   Примеров создано: {vid_count}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
