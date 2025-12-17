#!/usr/bin/env python
"""
Скрипт для проверки категорий видео и похожих видео.
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from gallery.models import PublicVideo, VideoCategory

def check_video_categories():
    print("=== Проверка категорий видео ===\n")
    
    # Получаем все видео категории
    categories = VideoCategory.objects.filter(is_active=True).order_by("name")
    print(f"Всего активных категорий: {categories.count()}\n")
    
    for category in categories:
        videos_count = PublicVideo.objects.filter(
            category=category,
            is_active=True
        ).count()
        print(f"Категория: {category.name} (slug: {category.slug})")
        print(f"  - Видео в категории: {videos_count}")
        
        # Показываем несколько видео из этой категории
        if videos_count > 0:
            videos = PublicVideo.objects.filter(
                category=category,
                is_active=True
            )[:3]
            for v in videos:
                print(f"    • {v.title or 'Без названия'} (slug: {v.slug})")
        print()
    
    # Проверяем видео без категории
    no_category_count = PublicVideo.objects.filter(
        category__isnull=True,
        is_active=True
    ).count()
    print(f"Видео без категории: {no_category_count}")
    
    # Проверяем конкретное видео, если есть
    print("\n=== Проверка конкретного видео ===")
    test_slug = "epic-fantasy-cliff-scene"
    try:
        video = PublicVideo.objects.get(slug=test_slug, is_active=True)
        print(f"Найдено видео: {video.title}")
        print(f"Категория: {video.category.name if video.category else 'НЕТ КАТЕГОРИИ!'}")
        print(f"Category ID: {video.category_id}")
        
        if video.category_id:
            # Проверяем похожие видео
            related = PublicVideo.objects.filter(
                category_id=video.category_id,
                is_active=True
            ).exclude(pk=video.pk).order_by("-likes_count", "-view_count", "-created_at")[:8]
            
            print(f"\nПохожих видео найдено: {related.count()}")
            for rv in related:
                print(f"  • {rv.title or 'Без названия'} (лайков: {rv.likes_count}, просмотров: {rv.view_count})")
        else:
            print("\n⚠️ У видео не установлена категория!")
            
    except PublicVideo.DoesNotExist:
        print(f"❌ Видео с slug '{test_slug}' не найдено")

if __name__ == "__main__":
    check_video_categories()
