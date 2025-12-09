"""
Скрипт для автоматического заполнения поддерживаемых типов референсов
для VideoModelConfiguration на основе model_id.
"""
import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models_video import VideoModelConfiguration


def populate_reference_types():
    """Заполняет supported_references для VideoModelConfiguration."""

    reference_rules = {
        "runware:201@1": ["referenceImages"],  # Wan2.5-Preview
        "bytedance": ["frameImages"],
        "klingai": ["frameImages"],
        "sora": ["frameImages"],
        "vidu": ["frameImages"],
        "runway": ["frameImages"],
        "pixverse": ["frameImages"],
    }

    updated_count = 0
    skipped_count = 0

    for config in VideoModelConfiguration.objects.all():
        model_id_lower = config.model_id.lower()

        # Пропускаем заполненные
        if config.supported_references:
            print(f"⏭️  Пропущено: {config.name} ({config.model_id}) - уже заполнено: {config.supported_references}")
            skipped_count += 1
            continue

        supported = []

        # Проверяем точное совпадение
        if config.model_id in reference_rules:
            supported = reference_rules[config.model_id]
        else:
            # Проверяем по провайдеру
            for provider, ref_types in reference_rules.items():
                if provider in model_id_lower:
                    supported = ref_types
                    break

        # I2V по умолчанию frameImages
        if not supported and config.category == VideoModelConfiguration.Category.I2V:
            supported = ["frameImages"]

        if supported:
            config.supported_references = supported
            config.save(update_fields=["supported_references"])
            print(f"✅ Обновлено: {config.name} ({config.model_id}) -> {supported}")
            updated_count += 1
        else:
            print(f"⚠️  Не определено: {config.name} ({config.model_id}) - категория {config.category}")
            skipped_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Обновлено: {updated_count}")
    print(f"⏭️  Пропущено: {skipped_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("🔧 Заполнение поддерживаемых типов референсов для VideoModelConfiguration...\n")
    populate_reference_types()
