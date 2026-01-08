#!/usr/bin/env python
"""
Скрипт для создания/обновления объекта Site с правильным доменом pixera.net
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from django.contrib.sites.models import Site
from django.db import connection

def fix_site_domain():
    """Создать или обновить Site объект с доменом pixera.net"""
    # Проверяем все существующие сайты
    all_sites = Site.objects.all()
    print(f"Существующие Sites в базе данных:")
    for s in all_sites:
        print(f"  ID: {s.id}, Domain: {s.domain}, Name: {s.name}")

    # Ищем Site с доменом pixera.net
    try:
        site_by_domain = Site.objects.get(domain='pixera.net')
        print(f"\n✓ Найден Site с доменом pixera.net (ID: {site_by_domain.id})")

        # Если это не ID=1, обновляем его ID через raw SQL
        if site_by_domain.id != 1:
            old_id = site_by_domain.id

            # Сначала удаляем Site с ID=1, если он существует
            try:
                old_site = Site.objects.get(id=1)
                old_site.delete()
                print(f"✓ Удален старый Site с ID=1 (домен: {old_site.domain})")
            except Site.DoesNotExist:
                pass

            # Используем raw SQL для обновления ID
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE django_site SET id = 1 WHERE id = %s",
                    [old_id]
                )
                print(f"✓ Обновлен ID Site с {old_id} на 1 через raw SQL")

    except Site.DoesNotExist:
        # Создаем новый Site
        # Сначала удаляем Site с ID=1, если он существует
        try:
            old_site = Site.objects.get(id=1)
            old_site.delete()
            print(f"✓ Удален старый Site с ID=1 (домен: {old_site.domain})")
        except Site.DoesNotExist:
            pass

        Site.objects.create(
            id=1,
            domain='pixera.net',
            name='Pixera'
        )
        print(f"✓ Создан новый Site объект с доменом pixera.net (ID: 1)")

    # Проверяем результат
    current_site = Site.objects.get(id=1)
    print(f"\n✓ Итоговые настройки Site:")
    print(f"  ID: {current_site.id}")
    print(f"  Domain: {current_site.domain}")
    print(f"  Name: {current_site.name}")

if __name__ == "__main__":
    fix_site_domain()
