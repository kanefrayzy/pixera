#!/usr/bin/env python
"""
Скрипт для проверки настроек OAuth провайдеров.
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_gallery.settings")
django.setup()

from django.conf import settings
from django.contrib.sites.models import Site

def check_oauth_settings():
    print("=== Проверка настроек OAuth ===\n")
    
    # Текущий сайт
    try:
        current_site = Site.objects.get_current()
        print(f"Текущий Site:")
        print(f"  Domain: {current_site.domain}")
        print(f"  Name: {current_site.name}")
        print()
    except Exception as e:
        print(f"❌ Ошибка получения Site: {e}\n")
    
    # Discord настройки
    print("Discord:")
    discord_id = os.getenv("DISCORD_CLIENT_ID")
    discord_secret = os.getenv("DISCORD_CLIENT_SECRET")
    
    if discord_id:
        print(f"  Client ID: {discord_id}")
        print(f"  Client Secret: {'*' * 20 if discord_secret else 'НЕ УСТАНОВЛЕН'}")
        
        # Ожидаемый redirect_uri
        domain = current_site.domain if 'current_site' in locals() else 'pixera.net'
        protocol = 'https' if not settings.DEBUG else 'http'
        
        # Django allauth использует этот формат
        redirect_uris = [
            f"{protocol}://{domain}/accounts/discord/login/callback/",
            f"{protocol}://{domain}/en/accounts/discord/login/callback/",
            f"{protocol}://{domain}/ru/accounts/discord/login/callback/",
        ]
        
        print("\n  Возможные redirect_uri для Discord:")
        for uri in redirect_uris:
            print(f"    - {uri}")
        
        print("\n  ⚠️ Убедитесь, что в Discord Developer Portal настроены эти URL!")
        print("     https://discord.com/developers/applications")
    else:
        print("  ❌ Discord не настроен (нет DISCORD_CLIENT_ID)")
    
    print("\n" + "="*60)
    print("\nДля исправления:")
    print("1. Зайдите в Discord Developer Portal:")
    print("   https://discord.com/developers/applications")
    print("2. Выберите ваше приложение (ID: {})".format(discord_id if discord_id else 'неизвестно'))
    print("3. OAuth2 → Redirects")
    print("4. Добавьте следующие URL:")
    for uri in redirect_uris if 'redirect_uris' in locals() else []:
        print(f"   {uri}")

if __name__ == "__main__":
    check_oauth_settings()
