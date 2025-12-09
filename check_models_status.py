#!/usr/bin/env python
"""
Проверка статуса моделей в БД и API
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models_video import VideoModelConfiguration
from generate.models import VideoModel
import json


def check_database():
    """Проверка моделей в БД"""
    print("=" * 70)
    print("ПРОВЕРКА МОДЕЛЕЙ В БАЗЕ ДАННЫХ")
    print("=" * 70)

    # VideoModelConfiguration
    print("\n1. VideoModelConfiguration:")
    configs = VideoModelConfiguration.objects.all()
    print(f"   Всего: {configs.count()}")
    print(f"   Активных: {VideoModelConfiguration.objects.filter(is_active=True).count()}")

    if configs.exists():
        print("\n   Список:")
        for config in configs:
            print(f"   - ID={config.id}, {config.name} ({config.model_id})")
            print(f"     Активна: {config.is_active}")
            print(f"     Категория: {config.category}")
            print(f"     Изображение: {'Да' if config.image else 'Нет'}")

    # VideoModel
    print("\n2. VideoModel (старая):")
    old_models = VideoModel.objects.all()
    print(f"   Всего: {old_models.count()}")

    if old_models.exists():
        print("\n   Список:")
        for model in old_models:
            print(f"   - ID={model.id}, {model.name} ({model.model_id})")


def check_api():
    """Проверка API"""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА API")
    print("=" * 70)

    from django.test import RequestFactory
    from generate.views_video_api import video_models_list

    factory = RequestFactory()
    request = factory.get('/generate/api/video/models')

    try:
        response = video_models_list(request)
        data = json.loads(response.content)

        print(f"\nHTTP Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Count: {data.get('count')}")

        if data.get('models'):
            print(f"\nМодели в API ({len(data['models'])} шт):")
            for model in data['models']:
                print(f"  - {model['name']} ({model['model_id']})")
                print(f"    Category: {model['category']}")
                print(f"    Token cost: {model['token_cost']}")
                print(f"    Image URL: {model.get('image_url', 'None')}")
        else:
            print("\n⚠️  API возвращает пустой список моделей!")

    except Exception as e:
        print(f"\n❌ Ошибка API: {e}")
        import traceback
        traceback.print_exc()


def create_test_model():
    """Создать тестовую модель"""
    print("\n" + "=" * 70)
    print("СОЗДАНИЕ ТЕСТОВОЙ МОДЕЛИ")
    print("=" * 70)

    try:
        model = VideoModelConfiguration.objects.create(
            name='Test Runway Model',
            model_id='runway:test@1',
            category='t2v',
            description='Тестовая модель для проверки',
            token_cost=50,
            max_duration=10,
            min_duration=2,
            min_width=512,
            max_width=1920,
            min_height=512,
            max_height=1080,
            min_motion_strength=0,
            max_motion_strength=100,
            default_motion_strength=45,
            min_fps=24,
            max_fps=60,
            default_fps=30,
            min_guidance_scale=1.0,
            max_guidance_scale=20.0,
            default_guidance_scale=7.5,
            min_inference_steps=10,
            max_inference_steps=100,
            default_inference_steps=50,
            order=0,
            provider='Runway',
            is_active=True,
            # Параметры
            resolution_1920x1080=True,
            resolution_1280x720=True,
            aspect_ratio_16_9=True,
            aspect_ratio_9_16=True,
            duration_5=True,
            duration_10=True,
        )

        print(f"✅ Тестовая модель создана!")
        print(f"   ID: {model.id}")
        print(f"   Название: {model.name}")
        print(f"   Model ID: {model.model_id}")

        return model.id

    except Exception as e:
        print(f"❌ Ошибка создания: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    print("\n" + "🔍" * 35)
    print("ДИАГНОСТИКА СИСТЕМЫ МОДЕЛЕЙ")
    print("🔍" * 35 + "\n")

    # 1. Проверяем БД
    check_database()

    # 2. Проверяем API
    check_api()

    # 3. Если моделей нет - создаём тестовую
    if VideoModelConfiguration.objects.count() == 0:
        print("\n⚠️  Моделей нет! Создаём тестовую...")
        model_id = create_test_model()

        if model_id:
            print("\n✅ Тестовая модель создана! Проверяем API снова...")
            check_api()

    print("\n" + "=" * 70)
    print("ИТОГИ")
    print("=" * 70)
    print(f"Моделей в БД: {VideoModelConfiguration.objects.count()}")
    print(f"Активных моделей: {VideoModelConfiguration.objects.filter(is_active=True).count()}")
    print("\nДля просмотра списка откройте:")
    print("  http://localhost:8000/generate/admin/video-models")
    print("=" * 70)
