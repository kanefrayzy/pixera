#!/usr/bin/env python
"""
Скрипт для автоматического назначения категорий существующим фото и видео.
Анализирует заголовок/описание и назначает подходящую категорию.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from gallery.models import PublicPhoto, PublicVideo, Category, VideoCategory
from django.db import transaction


def assign_photo_categories():
    """Назначить категории фото на основе анализа контента."""

    # Получаем или создаем категории для фото
    categories = {
        'nature': Category.objects.get_or_create(name='Nature', slug='nature')[0],
        'portraits': Category.objects.get_or_create(name='Portraits', slug='portraits')[0],
        'fantasy': Category.objects.get_or_create(name='Fantasy', slug='fantasy')[0],
        'art': Category.objects.get_or_create(name='Art', slug='art')[0],
        'other': Category.objects.get_or_create(name='Other', slug='other')[0],
    }

    # Ключевые слова для категорий
    keywords = {
        'nature': ['nature', 'landscape', 'forest', 'mountain', 'ocean', 'sky', 'tree', 'flower', 'sunset', 'sunrise'],
        'portraits': ['portrait', 'face', 'person', 'woman', 'man', 'girl', 'boy', 'people', 'human'],
        'fantasy': ['fantasy', 'magic', 'dragon', 'wizard', 'fairy', 'mythical', 'creature', 'epic'],
        'art': ['art', 'painting', 'drawing', 'illustration', 'artistic', 'creative'],
    }

    photos_without_category = PublicPhoto.objects.filter(category__isnull=True)
    updated_count = 0

    print(f"📸 Найдено {photos_without_category.count()} фото без категории")

    with transaction.atomic():
        for photo in photos_without_category:
            # Анализируем заголовок и описание
            text = f"{photo.title} {photo.caption}".lower()

            # Определяем категорию по ключевым словам
            assigned_category = None
            for cat_key, words in keywords.items():
                if any(word in text for word in words):
                    assigned_category = categories[cat_key]
                    break

            # Если не нашли подходящую - назначаем "Other"
            if not assigned_category:
                assigned_category = categories['other']

            photo.category = assigned_category
            photo.save(update_fields=['category'])
            updated_count += 1

            print(f"  ✅ Фото #{photo.pk} '{photo.title[:30]}...' → {assigned_category.name}")

    print(f"\n✅ Обновлено {updated_count} фото")


def assign_video_categories():
    """Назначить категории видео на основе анализа контента."""

    # Получаем или создаем категории для видео
    categories = {
        'animation': VideoCategory.objects.get_or_create(name='Animation', slug='animation')[0],
        'fantasy': VideoCategory.objects.get_or_create(name='Fantasy', slug='fantasy')[0],
        'nature': VideoCategory.objects.get_or_create(name='Nature', slug='nature')[0],
        'abstract': VideoCategory.objects.get_or_create(name='Abstract', slug='abstract')[0],
        'other': VideoCategory.objects.get_or_create(name='Other', slug='other')[0],
    }

    # Ключевые слова для категорий
    keywords = {
        'animation': ['animation', 'animated', 'cartoon', 'character', 'dancing', 'moving'],
        'fantasy': ['fantasy', 'epic', 'magic', 'dragon', 'wizard', 'cliff', 'castle'],
        'nature': ['nature', 'landscape', 'ocean', 'forest', 'mountain', 'sky', 'water'],
        'abstract': ['abstract', 'pattern', 'geometric', 'colorful', 'artistic'],
    }

    videos_without_category = PublicVideo.objects.filter(category__isnull=True)
    updated_count = 0

    print(f"\n🎬 Найдено {videos_without_category.count()} видео без категории")

    with transaction.atomic():
        for video in videos_without_category:
            # Анализируем заголовок и описание
            text = f"{video.title} {video.caption}".lower()

            # Определяем категорию по ключевым словам
            assigned_category = None
            for cat_key, words in keywords.items():
                if any(word in text for word in words):
                    assigned_category = categories[cat_key]
                    break

            # Если не нашли подходящую - назначаем "Other"
            if not assigned_category:
                assigned_category = categories['other']

            video.category = assigned_category
            video.save(update_fields=['category'])
            updated_count += 1

            print(f"  ✅ Видео #{video.pk} '{video.title[:30]}...' → {assigned_category.name}")

    print(f"\n✅ Обновлено {updated_count} видео")


def main():
    print("🚀 Начинаем назначение категорий...\n")

    try:
        assign_photo_categories()
        assign_video_categories()

        print("\n" + "="*60)
        print("✅ Все категории успешно назначены!")
        print("="*60)

        # Статистика
        photos_with_cat = PublicPhoto.objects.filter(category__isnull=False).count()
        photos_total = PublicPhoto.objects.count()
        videos_with_cat = PublicVideo.objects.filter(category__isnull=False).count()
        videos_total = PublicVideo.objects.count()

        print(f"\n📊 Статистика:")
        print(f"  Фото с категориями: {photos_with_cat}/{photos_total}")
        print(f"  Видео с категориями: {videos_with_cat}/{videos_total}")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
