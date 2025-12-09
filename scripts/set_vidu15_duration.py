#!/usr/bin/env python
"""
Приведение конфигурации моделей под рабочее состояние аккаунта Runware.

- Делаем Vidu 1.5 активной T2V-моделью с длительностью 4 сек (UI-лимит и серверная проверка)
- Деактивируем модели, которые дают invalidModel на текущем API ключе:
  runwayml:100@1, lumalabs:3@1, vidu:1@0, lumalabs:4@1, klingai:2@1, klingai:3@2
Запуск: python scripts/set_vidu15_duration.py
"""
import os
import sys
import django

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel

def main():
    changed = 0

    # 1) Vidu 1.5 — активна, max_duration = 4
    try:
        m = VideoModel.objects.get(model_id="vidu:1@5")
        updates = []
        if not m.is_active:
            m.is_active = True; updates.append("is_active=True")
        if m.max_duration != 4:
            m.max_duration = 4; updates.append("max_duration=4")
        if m.category != "t2v":
            m.category = "t2v"; updates.append("category=t2v")
        if m.order != 1:
            m.order = 1; updates.append("order=1")
        if updates:
            m.save(update_fields=["is_active","max_duration","category","order"])
            changed += 1
            print(f"✓ Обновлена Vidu 1.5 ({m.model_id}): {', '.join(updates)}")
        else:
            print("= Vidu 1.5 уже настроена корректно")
    except VideoModel.DoesNotExist:
        print("! Модель vidu:1@5 не найдена в БД")

    # 2) Деактивируем модели, которые на этом ключе дают invalidModel
    bad_ids = [
        "runwayml:100@1",
        "lumalabs:3@1",
        "vidu:1@0",
        "lumalabs:4@1",
        "klingai:2@1",
        "klingai:3@2",
    ]
    for mid in bad_ids:
        qs = VideoModel.objects.filter(model_id=mid, is_active=True)
        cnt = qs.update(is_active=False)
        if cnt:
            print(f"• Деактивирована: {mid}")
            changed += cnt

    # 3) Вывод активных моделей
    print("\nАктивные модели сейчас:")
    for m in VideoModel.objects.filter(is_active=True).order_by("category","order"):
        print(f"  {m.category.upper():4} | {m.model_id:16} | {m.name} (max_dur={m.max_duration})")

    print(f"\nИтого изменений: {changed}")

if __name__ == "__main__":
    main()
