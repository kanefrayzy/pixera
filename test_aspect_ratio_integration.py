#!/usr/bin/env python
"""
Тестирование интеграции aspect ratio селектора
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models_image import ImageModelConfiguration

def test_aspect_ratio_integration():
    """Тестируем, что aspect ratios корректно возвращаются в to_json()"""
    print("\n" + "="*70)
    print("ТЕСТ: Интеграция Aspect Ratio Selector")
    print("="*70)

    # Найдём модель с включёнными aspect ratios
    models = ImageModelConfiguration.objects.filter(is_active=True)

    print(f"\n📊 Найдено активных моделей: {models.count()}")

    for model in models[:3]:  # Проверим первые 3 модели
        print(f"\n{'─'*70}")
        print(f"🎨 Модель: {model.name} ({model.model_id})")
        print(f"{'─'*70}")

        # Получаем aspect ratios
        aspect_ratios = model.get_available_aspect_ratios()
        print(f"\n✅ Доступные aspect ratios ({len(aspect_ratios)}):")
        if aspect_ratios:
            for ratio in aspect_ratios:
                print(f"   • {ratio}")
        else:
            print("   (нет)")

        # Проверяем to_json()
        import json
        model_json = json.loads(model.to_json())

        print(f"\n🔍 Данные в to_json():")
        print(f"   • available_aspect_ratios: {model_json.get('available_aspect_ratios', [])}")
        print(f"   • min_width: {model_json.get('min_width')}")
        print(f"   • max_width: {model_json.get('max_width')}")
        print(f"   • min_height: {model_json.get('min_height')}")
        print(f"   • max_height: {model_json.get('max_height')}")

        # Проверка расчёта размеров
        if aspect_ratios:
            print(f"\n📐 Примеры расчёта размеров для 8,294,400 пикселей (~4K):")
            target_pixels = 8294400

            for ratio_str in aspect_ratios[:5]:  # Первые 5
                try:
                    # Парсим соотношение
                    parts = ratio_str.replace('_', ':').split(':')
                    if len(parts) == 2:
                        ratio_w = float(parts[0])
                        ratio_h = float(parts[1])
                        ratio = ratio_w / ratio_h

                        # Рассчитываем размеры
                        height = int((target_pixels / ratio) ** 0.5)
                        width = int(height * ratio)

                        # Ограничиваем по min/max модели
                        width = max(model.min_width, min(model.max_width, width))
                        height = max(model.min_height, min(model.max_height, height))

                        actual_pixels = width * height
                        print(f"   • {ratio_str:>8} → {width:4}×{height:4} = {actual_pixels:,} px")
                except Exception as e:
                    print(f"   • {ratio_str:>8} → ОШИБКА: {e}")

    print(f"\n{'='*70}")
    print("✅ Тест завершён")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_aspect_ratio_integration()
