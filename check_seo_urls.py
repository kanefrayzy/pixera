#!/usr/bin/env python
"""
Проверка SEO-friendly URLs для фото и видео.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from gallery.models import PublicPhoto, PublicVideo


def check_photos():
    """Проверить URL фото."""
    print("📸 Проверка URL фото:\n")

    photos = PublicPhoto.objects.filter(is_active=True).select_related('category')[:10]

    for photo in photos:
        url = photo.get_absolute_url()
        has_category = photo.category is not None

        status = "✅" if has_category else "⚠️"
        cat_name = photo.category.name if photo.category else "НЕТ КАТЕГОРИИ"

        print(f"{status} Фото #{photo.pk}: {photo.title[:40]}")
        print(f"   Категория: {cat_name}")
        print(f"   URL: {url}")
        print()


def check_videos():
    """Проверить URL видео."""
    print("\n🎬 Проверка URL видео:\n")

    videos = PublicVideo.objects.filter(is_active=True).select_related('category')[:10]

    for video in videos:
        url = video.get_absolute_url()
        has_category = video.category is not None

        status = "✅" if has_category else "⚠️"
        cat_name = video.category.name if video.category else "НЕТ КАТЕГОРИИ"

        print(f"{status} Видео #{video.pk}: {video.title[:40]}")
        print(f"   Категория: {cat_name}")
        print(f"   URL: {url}")
        print()


def main():
    print("="*70)
    print("🔍 ПРОВЕРКА SEO-FRIENDLY URLs")
    print("="*70 + "\n")

    check_photos()
    check_videos()

    print("="*70)
    print("✅ Проверка завершена!")
    print("="*70)


if __name__ == '__main__':
    main()
