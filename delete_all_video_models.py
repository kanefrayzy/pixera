#!/usr/bin/env python
"""
Удаление всех старых видео моделей
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoModel
from generate.models_video import VideoModelConfiguration


def delete_all_models():
    """Удаляет все видео модели"""
    print("=" * 70)
    print("УДАЛЕНИЕ ВСЕХ ВИДЕО МОДЕЛЕЙ")
    print("=" * 70)

    # Удаляем старые VideoModel
    print("\n1. Удаление старых VideoModel...")
    old_count = VideoModel.objects.count()
    if old_count > 0:
        VideoModel.objects.all().delete()
        print(f"✅ Удалено старых моделей: {old_count}")
    else:
        print("ℹ️  Старых моделей нет")

    # Удаляем VideoModelConfiguration
    print("\n2. Удаление VideoModelConfiguration...")
    new_count = VideoModelConfiguration.objects.count()
    if new_count > 0:
        VideoModelConfiguration.objects.all().delete()
        print(f"✅ Удалено новых моделей: {new_count}")
    else:
        print("ℹ️  Новых моделей нет")

    # Проверяем что всё удалено
    print("\n3. Проверка...")
    remaining_old = VideoModel.objects.count()
    remaining_new = VideoModelConfiguration.objects.count()

    if remaining_old == 0 and remaining_new == 0:
        print("✅ Все модели успешно удалены!")
        print("\n" + "=" * 70)
        print("Теперь добавляйте модели только через админ-панель:")
        print("http://localhost:8000/generate/admin/video-models/create")
        print("=" * 70)
        return True
    else:
        print(f"⚠️  Остались модели: VideoModel={remaining_old}, VideoModelConfiguration={remaining_new}")
        return False


if __name__ == '__main__':
    print("\n" + "🗑️ " * 35)
    print("ОЧИСТКА ВСЕХ ВИДЕО МОДЕЛЕЙ")
    print("🗑️ " * 35 + "\n")

    confirm = input("Вы уверены что хотите удалить ВСЕ видео модели? (yes/no): ")

    if confirm.lower() in ['yes', 'y', 'да']:
        success = delete_all_models()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Отменено")
        sys.exit(1)
