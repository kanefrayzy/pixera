#!/usr/bin/env python3
"""
Проверка конфигурации модели
"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models_image import ImageModelConfiguration

print("🔍 Проверка конфигурации моделей...\n")

models = ImageModelConfiguration.objects.filter(is_active=True)

for model in models:
    print(f"{'='*60}")
    print(f"Модель: {model.name}")
    print(f"{'='*60}\n")

    # Получаем JSON конфигурацию
    config_json = model.to_json()
    config = json.loads(config_json)

    print("📋 JSON конфигурация:")
    print(json.dumps(config, indent=2, ensure_ascii=False))

    print(f"\n📊 optional_fields:")
    optional_fields = config.get('optional_fields', {})
    for key, value in optional_fields.items():
        status = '✅' if value else '❌'
        print(f"   {status} {key}: {value}")

    print(f"\n{'='*60}\n")

print("\n✅ Проверка завершена!")
