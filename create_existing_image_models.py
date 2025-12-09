"""
Скрипт для создания моделей изображений для существующих моделей
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models_image import ImageModelConfiguration

# Создаем модели для существующих image models
models_data = [
    {
        'name': 'Стандартная',
        'model_id': 'runware:101@1',
        'slug': 'standard',
        'provider': 'Runware',
        'description': 'Универсальная модель: стабильное качество и быстрый отклик.',
        'token_cost': 10,
        'order': 1,
        'is_active': True,
        'is_beta': False,
        'is_premium': False,
        # Параметры
        'supports_steps': True,
        'min_steps': 1,
        'max_steps': 50,
        'default_steps': 20,
        'supports_cfg_scale': True,
        'min_cfg_scale': 1.0,
        'max_cfg_scale': 20.0,
        'default_cfg_scale': 7.0,
        'supports_scheduler': True,
        'supports_seed': True,
        'supports_negative_prompt': True,
        'supports_multiple_results': True,
        'max_number_results': 4,
        'supports_reference_images': False,
        # Разрешения
        'supports_custom_resolution': True,
        'min_width': 512,
        'max_width': 2048,
        'min_height': 512,
        'max_height': 2048,
        'resolution_512x512': True,
        'resolution_768x768': True,
        'resolution_1024x1024': True,
        'resolution_1024x768': True,
        'resolution_768x1024': True,
        # Optional fields - все параметры доступны
        'optional_fields': {
            'resolution': True,
            'steps': True,
            'cfg_scale': True,
            'scheduler': True,
            'seed': True,
            'negative_prompt': True,
            'number_results': True,
            'prompt': True,
            'auto_translate': True,
            'prompt_generator': True,
        }
    },
    {
        'name': 'Seedream',
        'model_id': 'bytedance:5@0',
        'slug': 'seedream',
        'provider': 'ByteDance',
        'description': 'Seedream: трендовые эффекты и стильные клипы.',
        'token_cost': 15,
        'order': 2,
        'is_active': True,
        'is_beta': False,
        'is_premium': False,
        'is_special_model': True,
        # Параметры
        'supports_steps': True,
        'min_steps': 1,
        'max_steps': 50,
        'default_steps': 20,
        'supports_cfg_scale': True,
        'min_cfg_scale': 1.0,
        'max_cfg_scale': 20.0,
        'default_cfg_scale': 7.0,
        'supports_seed': True,
        'supports_negative_prompt': False,
        'supports_multiple_results': True,
        'max_number_results': 4,
        'supports_reference_images': False,
        # Разрешения
        'supports_custom_resolution': True,
        'min_width': 512,
        'max_width': 2048,
        'min_height': 512,
        'max_height': 2048,
        'resolution_512x512': True,
        'resolution_768x768': True,
        'resolution_1024x1024': True,
        'resolution_1024x768': True,
        'resolution_768x1024': True,
        # Optional fields
        'optional_fields': {
            'resolution': True,
            'steps': True,
            'cfg_scale': True,
            'seed': True,
            'number_results': True,
            'prompt': True,
            'auto_translate': True,
            'prompt_generator': True,
        }
    },
    {
        'name': 'FLUX.1.1 [pro] Ultra',
        'model_id': 'bfl:2@2',
        'slug': 'flux-pro-ultra',
        'provider': 'Black Forest Labs',
        'description': 'FLUX.1.1 [pro] Ultra: премиум-реализм и максимальная детализация.',
        'token_cost': 15,
        'order': 3,
        'is_active': True,
        'is_beta': False,
        'is_premium': True,
        'is_special_model': True,
        'uses_jpeg_format': True,
        # Параметры
        'supports_steps': False,  # FLUX не поддерживает steps
        'supports_cfg_scale': False,  # FLUX не поддерживает CFG
        'supports_scheduler': False,
        'supports_seed': True,
        'supports_negative_prompt': False,
        'supports_multiple_results': True,
        'max_number_results': 4,
        'supports_reference_images': False,
        # Разрешения
        'supports_custom_resolution': True,
        'min_width': 512,
        'max_width': 2048,
        'min_height': 512,
        'max_height': 2048,
        'resolution_512x512': True,
        'resolution_768x768': True,
        'resolution_1024x1024': True,
        'resolution_1024x768': True,
        'resolution_768x1024': True,
        # Optional fields - минимальный набор для FLUX
        'optional_fields': {
            'resolution': True,
            'seed': True,
            'number_results': True,
            'prompt': True,
            'auto_translate': True,
            'prompt_generator': True,
        }
    },
]

print("Создание моделей изображений...")
created_count = 0
updated_count = 0

for data in models_data:
    model_id = data['model_id']

    # Проверяем, существует ли модель
    existing = ImageModelConfiguration.objects.filter(model_id=model_id).first()

    if existing:
        print(f"⚠️  Модель {data['name']} ({model_id}) уже существует, обновляем...")
        for key, value in data.items():
            setattr(existing, key, value)
        existing.save()
        updated_count += 1
        print(f"✅ Обновлена: {data['name']}")
    else:
        model = ImageModelConfiguration.objects.create(**data)
        created_count += 1
        print(f"✅ Создана: {data['name']} (ID: {model.pk})")

print(f"\n{'='*50}")
print(f"Создано новых моделей: {created_count}")
print(f"Обновлено существующих: {updated_count}")
print(f"Всего моделей в БД: {ImageModelConfiguration.objects.count()}")
print(f"{'='*50}")
