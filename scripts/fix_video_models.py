"""
Скрипт для исправления моделей видео:
1. Деактивирует модели только для I2V
2. Обновляет descriptions
"""

import os
import sys
import django

# Добавляем родительскую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoModel

def main():
    print("\n" + "="*80)
    print("ИСПРАВЛЕНИЕ МОДЕЛЕЙ ВИДЕО")
    print("="*80)

    # Деактивируем I2V-only модели для T2V
    i2v_only_models = [
        'klingai:3@2',  # KlingAI 1.6 Pro - только I2V
        'vidu:2@0',     # Vidu 2.0 - только I2V
    ]

    for model_id in i2v_only_models:
        try:
            model = VideoModel.objects.get(model_id=model_id)
            if model.is_active:
                model.is_active = False
                model.description = f"{model.description or model.name} (Только для I2V - Image-to-Video)"
                model.save()
                print(f"✓ Деактивирована {model_id}: {model.name}")
        except VideoModel.DoesNotExist:
            print(f"⚠ Модель {model_id} не найдена в БД")

    # Обновляем descriptions для активных моделей
    updates = {
        'google:2@0': 'Google Veo 2.0 - высокое качество, реалистичные текстуры',
        'google:3@0': 'Google Veo 3.0 - премиум качество, 8 секунд, генерация аудио',
        'vidu:1@1': 'Vidu 1.1 - быстрая генерация, хорошее качество',
        'vidu:1@5': 'Vidu 1.5 - улучшенная версия, 4 секунды, поддержка BGM',
    }

    for model_id, new_desc in updates.items():
        try:
            model = VideoModel.objects.get(model_id=model_id)
            model.description = new_desc
            model.save()
            print(f"✓ Обновлено описание {model_id}")
        except VideoModel.DoesNotExist:
            print(f"⚠ Модель {model_id} не найдена")

    print("\n" + "="*80)
    print("ТЕКУЩИЕ АКТИВНЫЕ МОДЕЛИ:")
    print("="*80)

    active_models = VideoModel.objects.filter(is_active=True).order_by('model_id')
    for model in active_models:
        print(f"\n{model.model_id}")
        print(f"  Название: {model.name}")
        print(f"  Описание: {model.description}")
        print(f"  Категория: {model.get_category_display()}")
        print(f"  Макс. длительность: {model.max_duration}s")
        print(f"  Стоимость: {model.token_cost} TOK")

    print("\n" + "="*80)
    print("ДЕАКТИВИРОВАННЫЕ МОДЕЛИ:")
    print("="*80)

    inactive_models = VideoModel.objects.filter(is_active=False).order_by('model_id')
    for model in inactive_models:
        print(f"\n{model.model_id}")
        print(f"  Название: {model.name}")
        print(f"  Причина: {model.description}")

    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
