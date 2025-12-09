#!/usr/bin/env python
"""
Обновить длительность для SORA 2 PRO (openai:3@2):
- max_duration = 12
Запуск:
  python scripts/update_sora_duration.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel

def main():
    try:
        obj = VideoModel.objects.get(model_id="openai:3@2")
    except VideoModel.DoesNotExist:
        print("Модель openai:3@2 не найдена")
        return

    changed = False
    if int(obj.max_duration or 0) != 12:
        obj.max_duration = 12
        changed = True
    if obj.name != "SORA 2 PRO":
        obj.name = "SORA 2 PRO"
        changed = True
    if changed:
        obj.save(update_fields=["name", "max_duration", "updated_at"])
        print(f"✓ Обновлено: {obj.model_id} -> max_duration={obj.max_duration}, name={obj.name}")
    else:
        print("Изменений не требуется")

    print("\nАктуальные активные модели:")
    for m in VideoModel.objects.filter(is_active=True).order_by('category', 'order'):
        print(f"  {m.category.upper():4} | {m.model_id:16} | {m.name} (max_dur={m.max_duration})")

if __name__ == "__main__":
    main()
