#!/usr/bin/env python
"""
Тест защиты от Tor/VPN - проверка на сервере
"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_gallery.settings')
django.setup()

from generate.models import DeviceFingerprint, FreeGrant, AbuseCluster, TokenGrantAttempt

def test_tor_protection():
    print("=" * 60)
    print("🔍 ПРОВЕРКА ЗАЩИТЫ ОТ TOR/VPN")
    print("=" * 60)
    print()
    
    # 1. Статистика
    print("📊 СТАТИСТИКА:")
    print(f"   Устройств: {DeviceFingerprint.objects.count()}")
    print(f"   Грантов: {FreeGrant.objects.count()}")
    print(f"   Кластеров: {AbuseCluster.objects.count()}")
    print(f"   Грантов без user: {FreeGrant.objects.filter(user__isnull=True).count()}")
    print()
    
    # 2. Последние устройства
    print("📱 ПОСЛЕДНИЕ 3 УСТРОЙСТВА:")
    devices = DeviceFingerprint.objects.all().order_by('-created_at')[:3]
    if not devices:
        print("   ❌ НЕТ УСТРОЙСТВ! Система не работает!")
    else:
        for i, d in enumerate(devices, 1):
            print(f"   {i}. Device #{d.id} (created: {d.created_at.strftime('%H:%M:%S')})")
            print(f"      FP: {d.fp[:32]}...")
            print(f"      GID: {d.gid[:32]}...")
            print(f"      UA_hash: {d.ua_hash[:32]}...")
            print(f"      Has grant: {'✅ YES' if d.free_grant else '❌ NO'}")
            print(f"      VPN detected: {'⚠️  YES' if d.is_vpn_detected else '✅ NO'}")
            print(f"      Bypass attempts: {d.bypass_attempts}")
    print()
    
    # 3. Кластеры
    print("🔗 ПОСЛЕДНИЕ 3 КЛАСТЕРА:")
    clusters = AbuseCluster.objects.all().order_by('-created_at')[:3]
    if not clusters:
        print("   ⚠️  НЕТ КЛАСТЕРОВ!")
    else:
        for i, c in enumerate(clusters, 1):
            idents = list(c.identifiers.all())
            print(f"   {i}. Cluster #{c.id}")
            print(f"      Jobs: {c.guest_jobs_used}/{c.guest_jobs_limit}")
            print(f"      Identifiers ({len(idents)}):")
            for ident in idents:
                print(f"        - {ident.kind}: {ident.value[:32]}...")
    print()
    
    # 4. Последние попытки
    print("📝 ПОСЛЕДНИЕ 5 ПОПЫТОК ПОЛУЧЕНИЯ ТОКЕНОВ:")
    attempts = TokenGrantAttempt.objects.all().order_by('-created_at')[:5]
    if not attempts:
        print("   ⚠️  НЕТ ПОПЫТОК!")
    else:
        for a in attempts:
            status = "✅ GRANTED" if a.was_granted else ("❌ BLOCKED" if a.was_blocked else "⚠️  DENIED")
            print(f"   {a.created_at.strftime('%H:%M:%S')} | {status}")
            if a.block_reason:
                print(f"      Reason: {a.block_reason}")
            print(f"      UA_hash: {a.ua_hash[:32]}...")
    print()
    
    # 5. Проверка дубликатов по UA
    print("🔍 ПРОВЕРКА ДУБЛИКАТОВ ПО UA_HASH:")
    from django.db.models import Count
    duplicates = DeviceFingerprint.objects.values('ua_hash').annotate(
        count=Count('id')
    ).filter(count__gt=1).order_by('-count')[:5]
    
    if not duplicates:
        print("   ✅ НЕТ ДУБЛИКАТОВ (это плохо для защиты от Tor!)")
        print("   📌 Если один браузер создаёт несколько устройств - защита НЕ работает!")
    else:
        print("   ⚠️  НАЙДЕНЫ ДУБЛИКАТЫ:")
        for dup in duplicates:
            ua_hash = dup['ua_hash']
            count = dup['count']
            devices_with_ua = DeviceFingerprint.objects.filter(ua_hash=ua_hash)
            grants = set([d.free_grant_id for d in devices_with_ua if d.free_grant_id])
            print(f"      UA_hash: {ua_hash[:32]}... -> {count} устройств, {len(grants)} грантов")
            if len(grants) > 1:
                print(f"         ❌ ПРОБЛЕМА! Один UA = несколько грантов (Tor обход работает!)")
            else:
                print(f"         ✅ OK: Все устройства используют один грант")
    print()
    
    # 6. Рекомендации
    print("=" * 60)
    print("🧪 ИНСТРУКЦИЯ ПО ТЕСТИРОВАНИЮ:")
    print("=" * 60)
    print("1. Откройте сайт в обычном браузере")
    print("2. Потратьте 5-10 токенов")
    print("3. Запомните количество оставшихся")
    print("4. Откройте Tor Browser")
    print("5. Зайдите на тот же сайт")
    print()
    print("ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
    print("✅ Должны увидеть ТЕ ЖЕ токены (не 30 новых!)")
    print("✅ В логах должна появиться запись: 'Using existing grant from cluster'")
    print()
    print("ЕСЛИ ВИДИТЕ 30 НОВЫХ ТОКЕНОВ:")
    print("❌ Защита НЕ работает!")
    print("❌ Проверьте, что middleware включен")
    print("❌ Проверьте, что кластеры создаются по UA_HASH")
    print("=" * 60)

if __name__ == '__main__':
    test_tor_protection()
