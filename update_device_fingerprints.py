#!/usr/bin/env python
"""
Скрипт для обновления существующих DeviceFingerprint записей.
Заполняет поле server_fp для старых записей.
"""

import os
import django
import hashlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from django.conf import settings
from generate.models import DeviceFingerprint


def compute_server_fp(ip_hash: str, ua_hash: str) -> str:
    """Вычислить серверный fingerprint."""
    raw = f"{ua_hash}|{ip_hash}|{settings.SECRET_KEY}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def main():
    print("🔧 Обновление существующих DeviceFingerprint записей...")
    
    # Находим все записи без server_fp
    devices = DeviceFingerprint.objects.filter(server_fp='')
    total = devices.count()
    
    if total == 0:
        print("✅ Все записи уже обновлены!")
        return
    
    print(f"📊 Найдено записей для обновления: {total}")
    
    updated = 0
    errors = 0
    
    for device in devices.iterator():
        try:
            if device.ip_hash and device.ua_hash:
                device.server_fp = compute_server_fp(device.ip_hash, device.ua_hash)
                device.save(update_fields=['server_fp'])
                updated += 1
                
                if updated % 100 == 0:
                    print(f"⏳ Обработано: {updated}/{total}")
            else:
                # Если нет данных для вычисления - используем текущий fp
                device.server_fp = device.fp
                device.save(update_fields=['server_fp'])
                updated += 1
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении device #{device.pk}: {e}")
            errors += 1
    
    print(f"\n✅ Готово!")
    print(f"   Обновлено: {updated}")
    print(f"   Ошибок: {errors}")
    print(f"   Всего: {total}")


if __name__ == '__main__':
    main()
