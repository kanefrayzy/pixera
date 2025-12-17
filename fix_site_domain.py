#!/usr/bin/env python
"""
Скрипт для исправления домена в Django Sites.
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from django.contrib.sites.models import Site

def fix_site_domain():
    print("=== Исправление домена в Django Sites ===\n")
    
    # Получаем текущий Site
    try:
        site = Site.objects.get_current()
        print(f"Текущий домен: {site.domain}")
        print(f"Текущее имя: {site.name}")
        
        # Обновляем на правильный домен
        site.domain = "pixera.net"
        site.name = "Pixera"
        site.save()
        
        print(f"\n✅ Домен обновлен!")
        print(f"Новый домен: {site.domain}")
        print(f"Новое имя: {site.name}")
        
        print("\nТеперь redirect_uri будут:")
        print("  - https://pixera.net/accounts/discord/login/callback/")
        print("  - https://pixera.net/en/accounts/discord/login/callback/")
        print("  - https://pixera.net/ru/accounts/discord/login/callback/")
        
        print("\n⚠️ Добавьте эти URL в Discord Developer Portal:")
        print("   https://discord.com/developers/applications/1431170432127602708/oauth2")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    fix_site_domain()
