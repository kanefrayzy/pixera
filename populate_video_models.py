#!/usr/bin/env python
"""
Скрипт для заполнения моделей видео в базе данных.
Запуск: python populate_video_models.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoModel

def populate_video_models():
    """Заполняет базу данных моделями видео с ценами."""
    
    models_data = [
        # Text-to-Video (лучшие по промту)
        {
            'name': 'Vidu 2.0',
            'model_id': 'vidu:2@0',
            'category': VideoModel.Category.T2V,
            'description': 'Стабильная физика, кинематографичные кадры, быстрые результаты',
            'token_cost': 27,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 1,
        },
        {
            'name': 'Vidu 1.5',
            'model_id': 'vidu:1@5',
            'category': VideoModel.Category.T2V,
            'description': 'Выгодная по цене, убедительный T2V в большинстве сцен',
            'token_cost': 18,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 2,
        },
        {
            'name': 'Veo 3.0 (Google) PRO',
            'model_id': 'google:3@0',
            'category': VideoModel.Category.T2V,
            'description': 'Самое высокое качество (кинокартинка), премиум модель',
            'token_cost': 45,
            'max_duration': 10,
            'max_resolution': '1920x1080',
            'order': 3,
        },
        
        # Image-to-Video (оживление фото)
        {
            'name': 'KlingAI 2.x STD',
            'model_id': 'klingai:2@1',
            'category': VideoModel.Category.I2V,
            'description': 'Отлично оживляет портреты и сцены по референс-фото',
            'token_cost': 36,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 4,
        },
        {
            'name': 'Vidu Q1',
            'model_id': 'vidu:1@1',
            'category': VideoModel.Category.I2V,
            'description': 'Хорошо сохраняет композицию исходного кадра',
            'token_cost': 22,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 5,
        },
        
        # Аниме-модель
        {
            'name': 'Vidu Q1 Classic (Anime)',
            'model_id': 'vidu:1@0',
            'category': VideoModel.Category.ANIME,
            'description': 'Стилизованный "классический" аниме-вид, идеален для 2D-стилистики',
            'token_cost': 18,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 6,
        },
        
        # Дополнительные модели
        {
            'name': 'Veo 2.0 (Google)',
            'model_id': 'google:2@0',
            'category': VideoModel.Category.T2V,
            'description': 'Быстрее/дешевле чем Veo 3, хорош для быстрых предпросмотров',
            'token_cost': 32,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 7,
        },
        {
            'name': 'Seedance 1.0 Pro (ByteDance)',
            'model_id': 'bytedance:2@1',
            'category': VideoModel.Category.T2V,
            'description': 'Сильные динамичные сцены, хорошая согласованность объектов',
            'token_cost': 40,
            'max_duration': 8,
            'max_resolution': '1920x1080',
            'order': 8,
        },
        {
            'name': 'KlingAI 1.6 Pro',
            'model_id': 'klingai:3@2',
            'category': VideoModel.Category.T2V,
            'description': 'Более стилистичная версия, уместна для эффектных клипов',
            'token_cost': 43,
            'max_duration': 10,
            'max_resolution': '1920x1080',
            'order': 9,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for model_data in models_data:
        model, created = VideoModel.objects.update_or_create(
            model_id=model_data['model_id'],
            defaults=model_data
        )
        
        if created:
            created_count += 1
            print(f"✓ Создана модель: {model.name} ({model.model_id}) - {model.token_cost} TOK")
        else:
            updated_count += 1
            print(f"↻ Обновлена модель: {model.name} ({model.model_id}) - {model.token_cost} TOK")
    
    print(f"\n{'='*60}")
    print(f"Итого: создано {created_count}, обновлено {updated_count}")
    print(f"Всего моделей в БД: {VideoModel.objects.count()}")
    print(f"{'='*60}")
    
    # Статистика по категориям
    print("\nСтатистика по категориям:")
    for category in VideoModel.Category:
        count = VideoModel.objects.filter(category=category.value, is_active=True).count()
        print(f"  {category.label}: {count} моделей")

if __name__ == '__main__':
    print("Заполнение моделей видео...\n")
    populate_video_models()
    print("\n✓ Готово!")
