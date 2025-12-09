"""
Скрипт для автоматического заполнения поддерживаемых типов референсов
для существующих видео-моделей на основе их model_id.
"""
import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel


def populate_reference_types():
    """Заполняет supported_references для существующих моделей."""

    # Определяем правила на основе анализа кода runware_client.py
    reference_rules = {
        # Wan2.5-Preview использует referenceImages вместо frameImages
        "runware:201@1": ["referenceImages"],

        # ByteDance модели поддерживают frameImages
        "bytedance": ["frameImages"],

        # KlingAI модели поддерживают frameImages
        "klingai": ["frameImages"],

        # Sora модели (пример)
        "sora": ["frameImages"],

        # Vidu модели (пример)
        "vidu": ["frameImages"],

        # Runway Gen-4 Turbo (пример)
        "runway": ["frameImages"],
    }

    updated_count = 0
    skipped_count = 0

    for model in VideoModel.objects.all():
        model_id_lower = model.model_id.lower()

        # Пропускаем модели, у которых уже заполнено поле
        if model.supported_references:
            print(f"⏭️  Пропущено: {model.name} ({model.model_id}) - уже заполнено: {model.supported_references}")
            skipped_count += 1
            continue

        # Определяем поддерживаемые референсы
        supported = []

        # Проверяем точное совпадение model_id
        if model.model_id in reference_rules:
            supported = reference_rules[model.model_id]
        else:
            # Проверяем по провайдеру в model_id
            for provider, ref_types in reference_rules.items():
                if provider in model_id_lower:
                    supported = ref_types
                    break

        # Если категория I2V и ничего не нашли, по умолчанию frameImages
        if not supported and model.category == VideoModel.Category.I2V:
            supported = ["frameImages"]

        # Если что-то нашли, обновляем
        if supported:
            model.supported_references = supported
            model.save(update_fields=["supported_references"])
            print(f"✅ Обновлено: {model.name} ({model.model_id}) -> {supported}")
            updated_count += 1
        else:
            print(f"⚠️  Не определено: {model.name} ({model.model_id}) - категория {model.category}")
            skipped_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Обновлено: {updated_count}")
    print(f"⏭️  Пропущено: {skipped_count}")
    print(f"{'='*60}")
    print("\n💡 Совет: Проверьте модели в админ-панели и при необходимости скорректируйте вручную.")


if __name__ == "__main__":
    print("🔧 Заполнение поддерживаемых типов референсов для видео-моделей...\n")
    populate_reference_types()
