#!/usr/bin/env python
"""
Деактивация неверных/устаревших видео-моделей и выстраивание правильного порядка.
Запуск: python scripts/deactivate_bad_video_models.py
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel

def main():
    invalid_exact = [
        # Неподдерживаемые/устаревшие AIR и старые псевдо-ID
        "vidu:2@0",
        "google:3@0",
        "google:2@0",
        "bytedance:2@1",
        "klingai:3@2",
        # Старый формат провайдера (provider/path) — должны быть в AIR
        "runwayml/gen3a_turbo",
        "lumalabs/dream-machine",
        "klingai/v1.5",
        "lumalabs/ray",
    ]

    print("=== Деактивация неверных моделей ===")
    deactivated = 0

    # Точно известные ID
    qs = VideoModel.objects.filter(model_id__in=invalid_exact, is_active=True)
    deactivated += qs.update(is_active=False)

    # Любые модели в старом формате "provider/path"
    for m in VideoModel.objects.filter(model_id__contains="/", is_active=True):
        m.is_active = False
        m.save(update_fields=["is_active"])
        deactivated += 1
        print(f" - деактивирована (старый формат): {m.model_id} — {m.name}")

    if deactivated:
        print(f"✓ Деактивировано моделей: {deactivated}")
    else:
        print("Нет активных неверных моделей")

    print("\n=== Актуальные модели и порядок ===")
    # Обновляем/гарантируем порядок и активность корректных моделей
    desired = [
        # T2V
        {"model_id": "runwayml:100@1", "name": "Runway Gen-3 Alpha Turbo", "category": "t2v", "order": 1, "is_active": True},
        {"model_id": "lumalabs:3@1", "name": "Luma Dream Machine", "category": "t2v", "order": 2, "is_active": True},
        {"model_id": "vidu:1@5", "name": "Vidu 1.5", "category": "t2v", "order": 3, "is_active": True},
        {"model_id": "vidu:1@0", "name": "Vidu 1.0", "category": "t2v", "order": 4, "is_active": True},
        # I2V
        {"model_id": "klingai:2@1", "name": "Kling AI v2.1 (I2V)", "category": "i2v", "order": 10, "is_active": True},
        {"model_id": "lumalabs:4@1", "name": "Luma Ray (I2V)", "category": "i2v", "order": 11, "is_active": True},
        {"model_id": "vidu:1@1", "name": "Vidu 1.1 (I2V)", "category": "i2v", "order": 12, "is_active": True},
    ]

    fixed = 0
    for d in desired:
        try:
            m = VideoModel.objects.get(model_id=d["model_id"])
            changed = False
            if m.category != d["category"]:
                m.category = d["category"]; changed = True
            if m.order != d["order"]:
                m.order = d["order"]; changed = True
            if not m.is_active:
                m.is_active = True; changed = True
            if changed:
                m.save(update_fields=["category", "order", "is_active"])
                fixed += 1
        except VideoModel.DoesNotExist:
            # если по какой-то причине отсутствует — пропускаем (создание не задача этого скрипта)
            pass

    if fixed:
        print(f"✓ Обновлен порядок/активность для: {fixed} моделей")

    print("\n=== Итоговый список активных моделей ===")
    for m in VideoModel.objects.filter(is_active=True).order_by("category", "order"):
        print(f" {m.category.upper():4} | {m.model_id:16} | {m.name} (order={m.order})")

if __name__ == "__main__":
    main()
