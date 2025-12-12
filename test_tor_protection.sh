#!/bin/bash
# Скрипт для проверки защиты от Tor на сервере

echo "🔍 ТЕСТ ЗАЩИТЫ ОТ TOR/VPN"
echo "========================="
echo ""

# 1. Проверяем количество устройств и грантов
echo "📊 Текущее состояние БД:"
docker-compose exec web python manage.py shell -c "
from generate.models import DeviceFingerprint, FreeGrant, AbuseCluster
print(f'Устройств: {DeviceFingerprint.objects.count()}')
print(f'Грантов: {FreeGrant.objects.count()}')
print(f'Кластеров: {AbuseCluster.objects.count()}')
print(f'Грантов без user: {FreeGrant.objects.filter(user__isnull=True).count()}')
"
echo ""

# 2. Проверяем последние созданные устройства
echo "📋 Последние 3 устройства:"
docker-compose exec web python manage.py shell -c "
from generate.models import DeviceFingerprint
devices = DeviceFingerprint.objects.all().order_by('-created_at')[:3]
for d in devices:
    print(f'ID: {d.id}')
    print(f'  FP: {d.fp[:20]}...')
    print(f'  Server FP: {d.server_fp[:20]}...')
    print(f'  GID: {d.gid[:20]}...')
    print(f'  UA_hash: {d.ua_hash[:20]}...')
    print(f'  IP_hash: {d.ip_hash[:20]}...')
    print(f'  Has grant: {d.free_grant is not None}')
    print(f'  VPN detected: {d.is_vpn_detected}')
    print(f'  Bypass attempts: {d.bypass_attempts}')
    print(f'  Created: {d.created_at}')
    print('---')
"
echo ""

# 3. Проверяем кластеры
echo "🔗 Последние 3 кластера:"
docker-compose exec web python manage.py shell -c "
from generate.models import AbuseCluster
clusters = AbuseCluster.objects.all().order_by('-created_at')[:3]
for c in clusters:
    idents = list(c.identifiers.all())
    print(f'Cluster #{c.id}')
    print(f'  Jobs: {c.guest_jobs_used}/{c.guest_jobs_limit}')
    print(f'  Identifiers: {len(idents)}')
    for i in idents:
        print(f'    {i.kind}: {i.value[:20]}...')
    print('---')
"
echo ""

# 4. Проверяем последние попытки получения токенов
echo "📝 Последние 5 попыток получения токенов:"
docker-compose exec web python manage.py shell -c "
from generate.models import TokenGrantAttempt
attempts = TokenGrantAttempt.objects.all().order_by('-created_at')[:5]
for a in attempts:
    status = 'GRANTED' if a.was_granted else ('BLOCKED' if a.was_blocked else 'DENIED')
    print(f'{a.created_at.strftime(\"%H:%M:%S\")} | {status} | {a.block_reason or \"OK\"}')
    print(f'  UA_hash: {a.ua_hash[:20]}...')
    print(f'  IP_hash: {a.ip_hash[:20]}...')
    print('---')
"
echo ""

# 5. Логи Docker
echo "📋 Последние 20 строк логов web контейнера (ищем fingerprint):"
docker-compose logs --tail=20 web | grep -i "fingerprint\|grant\|cluster" || echo "Нет логов с fingerprint/grant/cluster"
echo ""

echo "✅ Проверка завершена!"
echo ""
echo "🧪 ЧТО ТЕСТИРОВАТЬ:"
echo "1. Откройте сайт в обычном браузере"
echo "2. Потратьте несколько токенов"
echo "3. Запомните количество оставшихся токенов"
echo "4. Откройте Tor Browser и зайдите на сайт"
echo "5. ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: Должны увидеть те же токены (не 30 новых!)"
echo ""
echo "Если видите 30 новых токенов - защита НЕ работает!"
