#!/usr/bin/env python
"""
Переименовать модель openai:3@2 в SORA 2 PRO и обновить описание.

Запуск:
  python scripts/rename_openai_to_sora.py
"""
import os
import sys
import django

# PYTHONPATH -> корень проекта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from generate.models import VideoModel

def main():
    try:
        obj = VideoModel.objects.get(model_id="openai:3@2")
    except VideoModel.DoesNotExist:
        print("Модель openai:3@2 не найдена (создайте её скриптом add_openai_3_2.py)")
        return

    obj.name = "SORA 2 PRO"
    if not obj.description or "OpenAI" in obj.description:
        obj.description = "SORA 2 PRO — кинематографичный реализм, 30 FPS. Допустимая длительность: 4 / 8 / 12 сек."
    obj.save(update_fields=["name", "description", "updated_at"])
    print(f"✓ Переименовано: {obj.model_id} -> {obj.name}")
    print(f"Описание: {obj.description}")

    print("\nАктуальные активные модели:")
    for m in VideoModel.objects.filter(is_active=True).order_by('category', 'order'):
        print(f"  {m.category.upper():4} | {m.model_id:16} | {m.name} (max_dur={m.max_duration})")

if __name__ == "__main__":
    main()
