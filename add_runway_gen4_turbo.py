#!/usr/bin/env python
"""
Скрипт для добавления модели Runway Gen-4 Turbo в базу данных.
Запуск: python add_runway_gen4_turbo.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoModel

def add_runway_gen4_turbo():
    """Добавляет модель Runway Gen-4 Turbo для I2V и T2V."""

    # Runway Gen-4 Turbo для Text-to-Video
    runway_t2v_data = {
        'name': 'Runway Gen-4 Turbo',
        'model_id': 'runway:1@1',
        'category': VideoModel.Category.T2V,
        'description': 'Быстрая и качественная генерация видео из текста. Отличная детализация, плавные движения, кинематографичное качество.',
        'token_cost': 30,
        'max_duration': 10,
        'max_resolution': '1280x720',
        'order': 10,
        'is_active': True,
    }

    # Runway Gen-4 Turbo для Image-to-Video
    runway_i2v_data = {
        'name': 'Runway Gen-4 Turbo',
        'model_id': 'runway:1@1-i2v',
        'category': VideoModel.Category.I2V,
        'description': 'Оживление фотографий с высокой точностью. Сохраняет детали исходного изображения, создает естественные движения и кинематографичное качество.',
        'token_cost': 30,
        'max_duration': 10,
        'max_resolution': '1280x720',
        'order': 3,
        'is_active': True,
    }

    created_count = 0
    updated_count = 0

    # Добавляем T2V версию
    model_t2v, created = VideoModel.objects.update_or_create(
        model_id=runway_t2v_data['model_id'],
        defaults=runway_t2v_data
    )

    if created:
        created_count += 1
        print(f"✓ Создана модель T2V: {model_t2v.name} ({model_t2v.model_id}) - {model_t2v.token_cost} TOK")
    else:
        updated_count += 1
        print(f"↻ Обновлена модель T2V: {model_t2v.name} ({model_t2v.model_id}) - {model_t2v.token_cost} TOK")

    # Добавляем I2V версию
    model_i2v, created = VideoModel.objects.update_or_create(
        model_id=runway_i2v_data['model_id'],
        defaults=runway_i2v_data
    )

    if created:
        created_count += 1
        print(f"✓ Создана модель I2V: {model_i2v.name} ({model_i2v.model_id}) - {model_i2v.token_cost} TOK")
    else:
        updated_count += 1
        print(f"↻ Обновлена модель I2V: {model_i2v.name} ({model_i2v.model_id}) - {model_i2v.token_cost} TOK")

    print(f"\n{'='*60}")
    print(f"Итого: создано {created_count}, обновлено {updated_count}")
    print(f"Всего моделей в БД: {VideoModel.objects.count()}")
    print(f"{'='*60}")

    # Статистика по категориям
    print("\nСтатистика по категориям:")
    for category in VideoModel.Category:
        count = VideoModel.objects.filter(category=category.value, is_active=True).count()
        print(f"  {category.label}: {count} моделей")

    print("\n✓ Runway Gen-4 Turbo успешно добавлен в базу данных!")
    print("\nОсобенности модели:")
    print("  • Универсальная модель для T2V и I2V")
    print("  • Быстрая генерация (Turbo режим)")
    print("  • Высокое качество и детализация")
    print("  • Плавные кинематографичные движения")
    print("  • Максимальная длительность: 10 секунд")
    print("  • Разрешение: 1280x720")

if __name__ == '__main__':
    print("Добавление модели Runway Gen-4 Turbo...\n")
    add_runway_gen4_turbo()
