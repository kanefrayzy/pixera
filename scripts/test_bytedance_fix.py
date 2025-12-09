"""
Тестирование исправления ByteDance параметров.
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from ai_gallery.services.runware_client import generate_video_via_rest, RunwareVideoError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_bytedance_durations():
    """Тестирование ByteDance с разными длительностями."""

    model_id = "bytedance:1@1"
    prompt = "A beautiful sunset over the ocean with waves"

    # Тестируем разные длительности
    test_durations = [3, 5, 7, 10, 12]

    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ BYTEDANCE ПАРАМЕТРОВ")
    print("="*60)

    for duration in test_durations:
        print(f"\n--- Тест с duration={duration}s ---")
        try:
            result = generate_video_via_rest(
                prompt=prompt,
                model_id=model_id,
                duration=duration,
                aspect_ratio="16:9",
                resolution="864x480",
                camera_fixed=False
            )

            if result:
                print(f"✓ SUCCESS: duration={duration}s")
                # ByteDance возвращает dict с taskUUID (async), не video URL
                if isinstance(result, dict) and result.get('async'):
                    print(f"  Task UUID: {result.get('taskUUID')}")
                    print(f"  Mode: Async (ByteDance)")
                elif isinstance(result, str):
                    print(f"  Video URL: {result[:80]}...")
                else:
                    print(f"  Result: {result}")
            else:
                print(f"✗ FAILED: duration={duration}s - No result returned")

        except RunwareVideoError as e:
            print(f"✗ ERROR: duration={duration}s")
            print(f"  Message: {str(e)}")
        except Exception as e:
            print(f"✗ UNEXPECTED ERROR: duration={duration}s")
            print(f"  Message: {str(e)}")

    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60 + "\n")


def test_bytedance_resolutions():
    """Тестирование ByteDance с разными разрешениями."""

    model_id = "bytedance:1@1"
    prompt = "A cat playing with a ball"
    duration = 5

    # Тестируем разные разрешения для 16:9
    test_resolutions = [
        ("16:9", "1920x1088"),
        ("16:9", "864x480"),
        ("9:16", "480x864"),
        ("1:1", "640x640"),
    ]

    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ BYTEDANCE РАЗРЕШЕНИЙ")
    print("="*60)

    for aspect_ratio, resolution in test_resolutions:
        print(f"\n--- Тест с {aspect_ratio} @ {resolution} ---")
        try:
            result = generate_video_via_rest(
                prompt=prompt,
                model_id=model_id,
                duration=duration,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                camera_fixed=False
            )

            if result:
                print(f"✓ SUCCESS: {aspect_ratio} @ {resolution}")
                # ByteDance возвращает dict с taskUUID (async), не video URL
                if isinstance(result, dict) and result.get('async'):
                    print(f"  Task UUID: {result.get('taskUUID')}")
                    print(f"  Mode: Async (ByteDance)")
                elif isinstance(result, str):
                    print(f"  Video URL: {result[:80]}...")
                else:
                    print(f"  Result: {result}")
            else:
                print(f"✗ FAILED: {aspect_ratio} @ {resolution} - No result returned")

        except RunwareVideoError as e:
            print(f"✗ ERROR: {aspect_ratio} @ {resolution}")
            print(f"  Message: {str(e)}")
        except Exception as e:
            print(f"✗ UNEXPECTED ERROR: {aspect_ratio} @ {resolution}")
            print(f"  Message: {str(e)}")

    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🔧 Запуск тестов ByteDance исправлений...\n")

    # Проверяем наличие API ключа
    from django.conf import settings
    if not settings.RUNWARE_API_KEY:
        print("❌ ОШИБКА: RUNWARE_API_KEY не настроен в .env")
        sys.exit(1)

    print(f"✓ API ключ найден: {settings.RUNWARE_API_KEY[:20]}...")

    # Запускаем тесты
    print("\n1️⃣ Тестирование длительностей...")
    test_bytedance_durations()

    print("\n2️⃣ Тестирование разрешений...")
    test_bytedance_resolutions()

    print("\n✅ Все тесты завершены!")
