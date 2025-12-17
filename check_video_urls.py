#!/usr/bin/env python
"""
Скрипт для проверки URL видео.
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from gallery.models import PublicVideo
import requests

def check_video_urls():
    print("=== Проверка URL видео ===\n")
    
    # Получаем видео с ID 6, 7, 11 (из логов)
    video_ids = [6, 7, 11]
    
    for vid in video_ids:
        try:
            video = PublicVideo.objects.get(pk=vid)
            print(f"Видео #{vid}: {video.title or 'Без названия'}")
            print(f"  URL: {video.video_url}")
            print(f"  Категория: {video.category.name if video.category else 'Нет'}")
            print(f"  Активно: {video.is_active}")
            
            # Пробуем сделать HEAD запрос
            try:
                response = requests.head(video.video_url, timeout=5, allow_redirects=True)
                print(f"  Status: {response.status_code}")
                print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                print(f"  Content-Length: {response.headers.get('Content-Length', 'N/A')}")
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Ошибка доступа: {e}")
            
            print()
        except PublicVideo.DoesNotExist:
            print(f"Видео #{vid} не найдено\n")
    
    # Проверим все активные видео
    print("\n=== Все активные видео ===")
    all_videos = PublicVideo.objects.filter(is_active=True).order_by("pk")
    print(f"Всего: {all_videos.count()}\n")
    
    for v in all_videos:
        print(f"#{v.pk}: {v.title[:50] if v.title else 'Без названия'}")
        print(f"  URL: {v.video_url[:80]}...")
        print()

if __name__ == "__main__":
    check_video_urls()
