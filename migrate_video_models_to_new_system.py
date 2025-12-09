#!/usr/bin/env python
"""
Скрипт миграции существующих видео моделей в новую систему VideoModelConfiguration.
Переносит данные из старой таблицы VideoModel в новую VideoModelConfiguration.
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


def migrate_video_models():
    """Миграция существующих видео моделей"""

    print("🚀 Начинаем миграцию видео моделей...")
    print("=" * 60)

    # Получаем все активные модели из старой таблицы
    old_models = VideoModel.objects.filter(is_active=True).order_by('category', 'order')

    if not old_models.exists():
        print("⚠️  Не найдено активных моделей для миграции")
        return

    print(f"📊 Найдено моделей для миграции: {old_models.count()}")
    print()

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for old_model in old_models:
        try:
            # Проверяем, не существует ли уже модель с таким model_id
            if VideoModelConfiguration.objects.filter(model_id=old_model.model_id).exists():
                print(f"⏭️  Пропускаем {old_model.name} - уже существует")
                skipped_count += 1
                continue

            # Определяем категорию для новой системы
            if old_model.category == VideoModel.Category.I2V:
                category = VideoModelConfiguration.Category.I2V
                supports_i2v = True
            elif old_model.category == VideoModel.Category.ANIME:
                category = VideoModelConfiguration.Category.ANIME
                supports_i2v = False
            else:  # T2V
                category = VideoModelConfiguration.Category.T2V
                supports_i2v = False

            # Создаем новую модель с базовыми настройками
            new_model = VideoModelConfiguration.objects.create(
                name=old_model.name,
                model_id=old_model.model_id,
                description=old_model.description or "",
                category=category,
                token_cost=old_model.token_cost,

                # Разрешения - включаем стандартные
                resolution_1024x1024=True,
                resolution_1280x720=True,
                resolution_1920x1080=True,

                # Соотношения сторон
                aspect_ratio_1_1=True,
                aspect_ratio_16_9=True,
                aspect_ratio_9_16=True,

                # Длительность - берем из старой модели
                duration_4=True,
                duration_5=True,
                duration_8=True,
                duration_10=True,
                min_duration=2,
                max_duration=old_model.max_duration,

                # Движение камеры
                supports_camera_movement=True,
                camera_static=True,
                camera_pan_left=True,
                camera_pan_right=True,
                camera_zoom_in=True,
                camera_zoom_out=True,

                # I2V настройки
                supports_image_to_video=supports_i2v,
                supports_motion_strength=supports_i2v,

                # Дополнительные параметры
                supports_seed=True,
                supports_negative_prompt=True,

                # Форматы вывода
                supports_mp4=True,

                # Метаданные
                is_active=old_model.is_active,
                order=old_model.order,
                provider="Runware",
            )

            print(f"✅ Мигрирована: {new_model.name} ({new_model.model_id})")
            print(f"   Категория: {new_model.get_category_display()}")
            print(f"   Стоимость: {new_model.token_cost} TOK")
            print(f"   Макс. длительность: {new_model.max_duration}с")
            print()

            migrated_count += 1

        except Exception as e:
            print(f"❌ Ошибка при миграции {old_model.name}: {e}")
            error_count += 1
            continue

    print("=" * 60)
    print("📈 Результаты миграции:")
    print(f"   ✅ Успешно мигрировано: {migrated_count}")
    print(f"   ⏭️  Пропущено (уже существуют): {skipped_count}")
    print(f"   ❌ Ошибок: {error_count}")
    print()

    if migrated_count > 0:
        print("🎉 Миграция завершена успешно!")
        print()
        print("📝 Следующие шаги:")
        print("   1. Проверьте мигрированные модели в админ-панели")
        print("   2. Настройте дополнительные параметры для каждой модели")
        print("   3. Протестируйте генерацию видео с новыми моделями")
        print()
        print("🔗 Админ-панель: /generate/video/models/")
    else:
        print("ℹ️  Нет новых моделей для миграции")


if __name__ == '__main__':
    try:
        migrate_video_models()
    except KeyboardInterrupt:
        print("\n\n⚠️  Миграция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
