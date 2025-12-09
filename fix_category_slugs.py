#!/usr/bin/env python
"""
Исправление пустых slug у категорий.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from gallery.models import Category, VideoCategory

# Используем python-slugify для транслитерации кириллицы
try:
    from slugify import slugify
except ImportError:
    from django.utils.text import slugify


def fix_photo_categories():
    """Исправить slug у категорий фото."""
    print("📸 Исправление slug категорий фото:\n")

    categories = Category.objects.all()
    fixed = 0

    for cat in categories:
        if not cat.slug or cat.slug.strip() == '':
            old_slug = cat.slug
            cat.slug = slugify(cat.name)
            cat.save(update_fields=['slug'])
            fixed += 1
            print(f"  ✅ {cat.name}: '{old_slug}' → '{cat.slug}'")

    if fixed == 0:
        print("  ℹ️  Все категории фото уже имеют slug")

    print(f"\n✅ Исправлено {fixed} категорий фото")


def fix_video_categories():
    """Исправить slug у категорий видео."""
    print("\n🎬 Исправление slug категорий видео:\n")

    categories = VideoCategory.objects.all()
    fixed = 0

    for cat in categories:
        if not cat.slug or cat.slug.strip() == '':
            old_slug = cat.slug
            cat.slug = slugify(cat.name)
            cat.save(update_fields=['slug'])
            fixed += 1
            print(f"  ✅ {cat.name}: '{old_slug}' → '{cat.slug}'")

    if fixed == 0:
        print("  ℹ️  Все категории видео уже имеют slug")

    print(f"\n✅ Исправлено {fixed} категорий видео")


def main():
    print("="*70)
    print("🔧 ИСПРАВЛЕНИЕ SLUG КАТЕГОРИЙ")
    print("="*70 + "\n")

    fix_photo_categories()
    fix_video_categories()

    print("\n" + "="*70)
    print("✅ Все slug исправлены!")
    print("="*70)


if __name__ == '__main__':
    main()
