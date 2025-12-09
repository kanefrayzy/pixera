"""
Тестовый скрипт для проверки правильности формирования параметров для разных провайдеров видео.
"""
import sys
import os
import django

# Настройка Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from ai_gallery.services.runware_client import _build_provider_settings


def test_provider_settings():
    """Тестирует формирование providerSettings для всех провайдеров."""
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ ФОРМИРОВАНИЯ ПАРАМЕТРОВ ДЛЯ ПРОВАЙДЕРОВ")
    print("=" * 80)
    
    # 1. ByteDance
    print("\n1. ByteDance (bytedance:1@1)")
    print("-" * 40)
    settings = _build_provider_settings(
        'bytedance:1@1',
        camera_fixed=False
    )
    print(f"Settings: {settings}")
    expected = {'bytedance': {'cameraFixed': False}}
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ ByteDance OK")
    
    # 2. Google Veo
    print("\n2. Google Veo (google:3@0)")
    print("-" * 40)
    settings = _build_provider_settings(
        'google:3@0',
        enhance_prompt=True,
        generate_audio=True
    )
    print(f"Settings: {settings}")
    expected = {'google': {'enhancePrompt': True, 'generateAudio': True}}
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ Google Veo OK")
    
    # 3. MiniMax
    print("\n3. MiniMax (minimax:1@1)")
    print("-" * 40)
    settings = _build_provider_settings(
        'minimax:1@1',
        prompt_optimizer=True
    )
    print(f"Settings: {settings}")
    expected = {'minimax': {'promptOptimizer': True}}
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ MiniMax OK")
    
    # 4. PixVerse - с эффектом
    print("\n4. PixVerse с эффектом (pixverse:1@3)")
    print("-" * 40)
    settings = _build_provider_settings(
        'pixverse:1@3',
        style='anime',
        effect='jiggle jiggle',
        motion_mode='fast',
        sound_effect_switch=True,
        sound_effect_content='upbeat music'
    )
    print(f"Settings: {settings}")
    expected = {
        'pixverse': {
            'style': 'anime',
            'effect': 'jiggle jiggle',
            'motionMode': 'fast',
            'soundEffectSwitch': True,
            'soundEffectContent': 'upbeat music'
        }
    }
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ PixVerse с эффектом OK")
    
    # 5. PixVerse - с движением камеры
    print("\n5. PixVerse с движением камеры (pixverse:1@4)")
    print("-" * 40)
    settings = _build_provider_settings(
        'pixverse:1@4',
        camera_movement='zoom_in',
        motion_mode='normal'
    )
    print(f"Settings: {settings}")
    expected = {
        'pixverse': {
            'cameraMovement': 'zoom_in',
            'motionMode': 'normal'
        }
    }
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ PixVerse с движением камеры OK")
    
    # 6. Vidu
    print("\n6. Vidu (vidu:1@5)")
    print("-" * 40)
    settings = _build_provider_settings(
        'vidu:1@5',
        movement_amplitude='medium',
        bgm=True,
        style='anime'
    )
    print(f"Settings: {settings}")
    expected = {
        'vidu': {
            'movementAmplitude': 'medium',
            'bgm': True,
            'style': 'anime'
        }
    }
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ Vidu OK")
    
    # 7. KlingAI (без специфичных настроек)
    print("\n7. KlingAI (klingai:5@3)")
    print("-" * 40)
    settings = _build_provider_settings('klingai:5@3')
    print(f"Settings: {settings}")
    expected = {}
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ KlingAI OK (нет специфичных настроек)")
    
    # 8. Пустые параметры
    print("\n8. Провайдер без параметров")
    print("-" * 40)
    settings = _build_provider_settings('bytedance:1@1')
    print(f"Settings: {settings}")
    expected = {'bytedance': {'cameraFixed': False}}  # default значение
    assert settings == expected, f"Expected {expected}, got {settings}"
    print("✓ Пустые параметры OK")
    
    print("\n" + "=" * 80)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! ✓")
    print("=" * 80)


def test_full_payload_examples():
    """Показывает примеры полных payload для разных моделей."""
    
    print("\n" + "=" * 80)
    print("ПРИМЕРЫ ПОЛНЫХ PAYLOAD ДЛЯ РАЗНЫХ МОДЕЛЕЙ")
    print("=" * 80)
    
    import uuid
    
    # ByteDance
    print("\n1. ByteDance Text-to-Video")
    print("-" * 40)
    payload = {
        "taskType": "videoInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": "A cat playing with a ball",
        "model": "bytedance:1@1",
        "duration": 8.0,
        "width": 960,
        "height": 960,
        "outputType": "URL",
        "providerSettings": _build_provider_settings('bytedance:1@1', camera_fixed=False)
    }
    print(f"Payload: {payload}")
    
    # Google Veo 3 с аудио
    print("\n2. Google Veo 3 с аудио")
    print("-" * 40)
    payload = {
        "taskType": "videoInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": "A person walking in a park",
        "model": "google:3@0",
        "duration": 8.0,
        "width": 1280,
        "height": 720,
        "outputType": "URL",
        "providerSettings": _build_provider_settings(
            'google:3@0',
            enhance_prompt=True,
            generate_audio=True
        )
    }
    print(f"Payload: {payload}")
    
    # PixVerse с эффектом
    print("\n3. PixVerse с эффектом")
    print("-" * 40)
    payload = {
        "taskType": "videoInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": "A person dancing",
        "model": "pixverse:1@3",
        "duration": 8.0,
        "width": 1080,
        "height": 1920,
        "outputType": "URL",
        "providerSettings": _build_provider_settings(
            'pixverse:1@3',
            style='anime',
            effect='jiggle jiggle',
            motion_mode='fast'
        )
    }
    print(f"Payload: {payload}")
    
    # Vidu с фоновой музыкой
    print("\n4. Vidu с фоновой музыкой")
    print("-" * 40)
    payload = {
        "taskType": "videoInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": "A sunset over mountains",
        "model": "vidu:1@5",
        "duration": 4.0,  # Vidu 1.5 использует 4 секунды
        "width": 1280,
        "height": 720,
        "outputType": "URL",
        "providerSettings": _build_provider_settings(
            'vidu:1@5',
            movement_amplitude='medium',
            bgm=True,
            style='general'
        )
    }
    print(f"Payload: {payload}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    try:
        test_provider_settings()
        test_full_payload_examples()
        print("\n✓ Все проверки завершены успешно!")
    except AssertionError as e:
        print(f"\n✗ ОШИБКА: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ НЕОЖИДАННАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
