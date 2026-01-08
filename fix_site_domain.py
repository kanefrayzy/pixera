#!/usr/bin/env python
"""
Скрипт для создания/обновления объекта Site с правильным доменом pixera.net
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from django.contrib.sites.models import Site

def fix_site_domain():
    """Создать или обновить Site объект с доменом pixera.net"""
    site, created = Site.objects.get_or_create(
        id=1,
        defaults={
            'domain': 'pixera.net',
            'name': 'Pixera'
        }
    )
    
    if not created:
        # Обновляем существующий сайт
        site.domain = 'pixera.net'
        site.name = 'Pixera'
        site.save()
        print(f"✓ Обновлен Site объект: {site.domain} (ID: {site.id})")
    else:
        print(f"✓ Создан новый Site объект: {site.domain} (ID: {site.id})")
    
    # Проверяем результат
    current_site = Site.objects.get(id=1)
    print(f"\nТекущие настройки Site:")
    print(f"  ID: {current_site.id}")
    print(f"  Domain: {current_site.domain}")
    print(f"  Name: {current_site.name}")

if __name__ == "__main__":
    fix_site_domain()
