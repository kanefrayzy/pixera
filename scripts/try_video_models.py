#!/usr/bin/env python
"""
Перебор кандидатных ID видео-моделей для Runware API.
Печатает результат для каждой модели (успех/ошибка).
Запуск: python scripts/try_video_models.py
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from ai_gallery.services.runware_client import generate_video_via_rest, RunwareVideoError

CANDIDATES = [
    # Популярные в доках варианта
    "vidu:2@0",
    "vidu:1@5",
    "vidu:1@0",
    "runwayml:100@1",
    "lumalabs:3@1",
    "klingai:3@2",
    "klingai:2@1",
    "lumalabs:4@1",
    # Из .env по умолчанию (на случай универсальной модели)
    "rundiffusion:130@100",
]

def try_model(mid: str):
    print(f"\n=== ТЕСТ МОДЕЛИ: {mid} ===")
    try:
        res = generate_video_via_rest(
            prompt="Quick test prompt for compatibility",
            model_id=mid,
            duration=5,
        )
        print("OK: запрос принят Runware")
        print(f" taskUUID={res.get('taskUUID')}")
        return True
    except RunwareVideoError as e:
        print(f"ERR: {e}")
        return False
    except Exception as e:
        print(f"UNEXPECTED: {e}")
        return False

def main():
    ok = 0
    for m in CANDIDATES:
        if try_model(m):
            ok += 1
    print(f"\nИТОГО: success={ok}/{len(CANDIDATES)}")

if __name__ == "__main__":
    main()
