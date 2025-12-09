#!/usr/bin/env python
"""
Скрипт для обновления моделей видео на правильные AIR идентификаторы Runware.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import VideoModel

# Правильные AIR идентификаторы из документации Runware
CORRECT_MODELS = [
    # Text-to-Video модели
    {
        'old_id': 'runwayml/gen3a_turbo',
        'new_id': 'runwayml:100@1',
        'name': 'Runway Gen-3 Alpha Turbo',
        'category': 't2v',
        'description': 'Быстрая генерация видео из текста (5-10 сек)',
        'token_cost': 15,
        'max_duration': 10,
        'max_resolution': '1280x768',
        'order': 1
    },
    {
        'old_id': 'lumalabs/dream-machine',
        'new_id': 'lumalabs:3@1',
        'name': 'Luma Dream Machine',
        'category': 't2v',
        'description': 'Креативная генерация видео (до 5 сек)',
        'token_cost': 14,
        'max_duration': 5,
        'max_resolution': '1920x1080',
        'order': 2
    },
    {
        'old_id': 'vidu:1@5',
        'new_id': 'vidu:1@5',  # Уже правильный формат
        'name': 'Vidu 1.5',
        'category': 't2v',
        'description': 'Высококачественная генерация видео (до 8 сек)',
        'token_cost': 18,
        'max_duration': 8,
        'max_resolution': '1920x1080',
        'order': 3
    },
    {
        'old_id': 'vidu:1@0',
        'new_id': 'vidu:1@0',  # Уже правильный формат
        'name': 'Vidu 1.0',
        'category': 't2v',
        'description': 'Стандартная генерация видео (до 5 сек)',
        'token_cost': 12,
        'max_duration': 5,
        'max_resolution': '1280x720',
        'order': 4
    },
    
    # Image-to-Video модели
    {
        'old_id': 'klingai/v1.5',
        'new_id': 'klingai:2@1',
        'name': 'Kling AI v1.5 (I2V)',
        'category': 'i2v',
        'description': 'Анимация изображений с высокой детализацией',
        'token_cost': 20,
        'max_duration': 5,
        'max_resolution': '1920x1080',
        'order': 10
    },
    {
        'old_id': 'klingai:2@1',
        'new_id': 'klingai:2@1',  # Уже правильный формат
        'name': 'Kling AI v2.1 (I2V)',
        'category': 'i2v',
        'description': 'Продвинутая анимация изображений',
        'token_cost': 20,
        'max_duration': 5,
        'max_resolution': '1920x1080',
        'order': 11
    },
    {
        'old_id': 'lumalabs/ray',
        'new_id': 'lumalabs:4@1',
        'name': 'Luma Ray (I2V)',
        'category': 'i2v',
        'description': 'Реалистичная анимация изображений',
        'token_cost': 16,
        'max_duration': 5,
        'max_resolution': '1920x1080',
        'order': 12
    },
    {
        'old_id': 'vidu:1@1',
        'new_id': 'vidu:1@1',  # Уже правильный формат
        'name': 'Vidu 1.1 (I2V)',
        'category': 'i2v',
        'description': 'Плавная анимация из изображения',
        'token_cost': 18,
        'max_duration': 4,
        'max_resolution': '1920x1080',
        'order': 13
    },
]

def update_models():
    """Обновляет модели на правильные AIR идентификаторы."""
    print("🔄 Обновление моделей видео на AIR формат...")
    print("=" * 60)
    
    updated_count = 0
    created_count = 0
    
    for model_data in CORRECT_MODELS:
        old_id = model_data['old_id']
        new_id = model_data['new_id']
        
        # Пытаемся найти модель по старому или новому ID
        model = None
        try:
            model = VideoModel.objects.get(model_id=old_id)
            if old_id != new_id:
                print(f"\n✏️  Обновление: {old_id} → {new_id}")
            else:
                print(f"\n✏️  Обновление: {old_id}")
        except VideoModel.DoesNotExist:
            # Пробуем найти по новому ID
            try:
                model = VideoModel.objects.get(model_id=new_id)
                print(f"\n✏️  Обновление существующей: {new_id}")
            except VideoModel.DoesNotExist:
                pass
        
        if model:
            # Обновляем все поля
            model.model_id = new_id
            model.name = model_data['name']
            model.category = model_data['category']
            model.description = model_data['description']
            model.token_cost = model_data['token_cost']
            model.max_duration = model_data['max_duration']
            model.max_resolution = model_data['max_resolution']
            model.order = model_data['order']
            model.is_active = True
            model.save()
            
            print(f"   ✅ Обновлено: {model.name}")
            updated_count += 1
        else:
            # Создаём новую модель
            print(f"\n➕ Создание новой модели: {new_id}")
            
            VideoModel.objects.create(
                model_id=new_id,
                name=model_data['name'],
                category=model_data['category'],
                description=model_data['description'],
                token_cost=model_data['token_cost'],
                max_duration=model_data['max_duration'],
                max_resolution=model_data['max_resolution'],
                order=model_data['order'],
                is_active=True
            )
            
            print(f"   ✅ Создано: {model_data['name']}")
            created_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Готово!")
    print(f"   Обновлено: {updated_count}")
    print(f"   Создано: {created_count}")
    print("\n📋 Текущие модели в базе:")
    print("-" * 60)
    
    for model in VideoModel.objects.filter(is_active=True).order_by('category', 'order'):
        print(f"   {model.category.upper():5} | {model.model_id:20} | {model.name}")

if __name__ == '__main__':
    update_models()
