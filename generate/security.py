# generate/security.py
"""
Железная система безопасности для гостевого режима.
4-этапная защита от обхода лимита токенов.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.db.models import Q

from .models import FreeGrant, DeviceFingerprint, TokenGrantAttempt, AbuseCluster

log = logging.getLogger(__name__)


def get_device_identifiers(request: HttpRequest) -> dict:
    """
    Извлечь все идентификаторы устройства из request.
    Использует данные из DeviceFingerprintMiddleware.
    Приоритет клиентскому fingerprint.
    """
    return {
        'fp': getattr(request, 'device_fp', ''),  # Основной FP (клиентский или fallback)
        'client_fp': getattr(request, 'device_client_fp', ''),  # Клиентский FP
        'server_fp': getattr(request, 'device_server_fp', ''),  # Серверный FP
        'gid': getattr(request, 'device_gid', ''),
        'ip_hash': getattr(request, 'device_ip_hash', ''),
        'ua_hash': getattr(request, 'device_ua_hash', ''),
        'session_key': getattr(request, 'device_session_key', ''),
        'first_ip': _extract_ip(request),
    }


def _extract_ip(request: HttpRequest) -> Optional[str]:
    """Извлечь IP адрес из request."""
    # Пробуем получить из заголовков
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
    if xff:
        return xff.split(',')[0].strip()

    xoff = request.META.get('HTTP_X_ORIGINAL_FORWARDED_FOR', '').strip()
    if xoff:
        return xoff.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR', '').strip()


def _find_cluster_grant(cluster: AbuseCluster) -> Optional[FreeGrant]:
    """Ищем существующий FreeGrant внутри кластера по любому из идентификаторов."""
    try:
        idents = list(cluster.identifiers.all())
        fps = [i.value for i in idents if i.kind == 'fp']
        gids = [i.value for i in idents if i.kind == 'gid']
        ips = [i.value for i in idents if i.kind == 'ip']
        uas = [i.value for i in idents if i.kind == 'ua']

        if not (fps or gids or ips or uas):
            return None

        q = Q()
        if fps:
            q |= Q(fp__in=fps)
        if gids:
            q |= Q(gid__in=gids)
        if ips:
            q |= Q(ip_hash__in=ips)
        if uas:
            q |= Q(ua_hash__in=uas)

        return FreeGrant.objects.filter(q).order_by('created_at').first()
    except Exception as e:
        log.error(f"Cluster grant search failed: {e}")
        return None


@transaction.atomic
def ensure_guest_grant_with_security(request: HttpRequest) -> Tuple[Optional[FreeGrant], Optional[DeviceFingerprint], str]:
    """
    УЛУЧШЕННАЯ ЛОГИКА получения/создания гранта для гостя.

    Возвращает: (grant, device, error_message)

    СТРАТЕГИЯ (защита от Tor/VPN):
    1. Создаём/находим КЛАСТЕР по UA_HASH (самый стабильный параметр)
    2. Ищем существующий ГРАНТ в кластере
    3. Если грант найден - используем его (даже если IP/FP изменились)
    4. Если грант не найден - создаём ОДИН грант на весь кластер
    5. Устройства привязываем к кластеру (для статистики)

    КЛЮЧЕВОЕ ОТЛИЧИЕ:
    - UA_HASH не меняется в Tor Browser (один и тот же браузер)
    - Один грант на кластер UA_HASH (а не на каждый IP/FP)
    - IP и FP только для статистики и VPN-детекта
    """
    ids = get_device_identifiers(request)

    fp = ids['fp']
    client_fp = ids['client_fp']
    server_fp = ids['server_fp']
    gid = ids['gid']
    ip_hash = ids['ip_hash']
    ua_hash = ids['ua_hash']
    session_key = ids['session_key']
    first_ip = ids['first_ip']

    # КЛЮЧЕВАЯ ПРОВЕРКА: UA_HASH обязателен (он не меняется в Tor!)
    if not ua_hash:
        log.error("UA_HASH is missing - cannot track user")
        return None, None, "Ошибка идентификации браузера"

    # ШАГ 1: КЛАСТЕР - главный механизм идентификации
    # Используем UA_HASH как основной идентификатор (стабилен в Tor)
    # FP и GID могут меняться (Tor очищает), но UA остаётся
    try:
        # Создаём кластер по UA_HASH (+ FP, GID если есть)
        cluster = AbuseCluster.ensure_for(
            ua_hash=ua_hash,
            fp=fp if fp else None,
            gid=gid if gid else None,
            ip_hash=None,  # НЕ используем IP для кластеризации!
        )
    except Exception as e:
        log.error(f"Error ensuring cluster: {e}")
        return None, None, "Ошибка системы безопасности"

    # ШАГ 2: Ищем существующий грант в кластере
    grant = _find_cluster_grant(cluster)
    
    if grant:
        # Найден существующий грант в кластере
        # Проверяем доступность
        if grant.is_bound_to_user:
            log.warning(f"Grant {grant.pk} is bound to user, cluster {cluster.pk}")
            return None, None, "Грант уже привязан к пользователю"
        
        # Обновляем метаданные гранта (актуализируем)
        if fp and grant.fp != fp:
            grant.fp = fp
        if gid and grant.gid != gid:
            grant.gid = gid
        if ip_hash and grant.ip_hash != ip_hash:
            grant.ip_hash = ip_hash
        if ua_hash and grant.ua_hash != ua_hash:
            grant.ua_hash = ua_hash
        grant.save()
        
        log.info(f"Using existing grant {grant.pk} from cluster {cluster.pk}")
        
        # Создаём/обновляем устройство (для статистики)
        device = None
        try:
            device, _ = DeviceFingerprint.get_or_create_device(
                fp=fp or server_fp,
                gid=gid,
                ip_hash=ip_hash,
                ua_hash=ua_hash,
                server_fp=server_fp,
                first_ip=first_ip,
                session_key=session_key
            )
            if device and not device.free_grant:
                device.free_grant = grant
                device.save()
        except Exception as e:
            log.error(f"Error updating device: {e}")
        
        return grant, device, ""

    # ШАГ 3: Создаём устройство
    try:
        device, created = DeviceFingerprint.get_or_create_device(
            fp=fp or server_fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            server_fp=server_fp,
            first_ip=first_ip,
            session_key=session_key
        )
    except Exception as e:
        log.error(f"Error creating device: {e}")
        return None, None, "Ошибка системы безопасности"

    # ШАГ 4: Проверка блокировки устройства
    can_get, reason = device.can_get_tokens()
    if not can_get:
        TokenGrantAttempt.objects.create(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            session_key=session_key,
            ip_address=first_ip,
            was_granted=False,
            was_blocked=True,
            block_reason=reason,
            device=device
        )
        return None, device, reason

    # ШАГ 5: Создаём НОВЫЙ грант (только если нет в кластере)
    # Один грант на весь кластер UA_HASH
    try:
        grant = FreeGrant.objects.create(
            fp=fp,
            gid=gid,
            ua_hash=ua_hash,
            ip_hash=ip_hash,
            first_ip=first_ip,
            total=30,
            consumed=0
        )
        
        # Привязываем грант к устройству
        device.free_grant = grant
        device.save(update_fields=['free_grant', 'updated_at'])
        
        # Логируем создание нового гранта
        TokenGrantAttempt.objects.create(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            session_key=session_key,
            ip_address=first_ip,
            was_granted=True,
            was_blocked=False,
            block_reason='',
            device=device
        )
        
        log.info(f"Created new grant {grant.pk} for cluster {cluster.pk}, device {device.pk}")
        return grant, device, ""
        
    except Exception as e:
        log.error(f"Failed to create grant: {e}")
        return None, device, "Не удалось создать грант"




@transaction.atomic
def check_and_spend_guest_tokens(
    request: HttpRequest,
    amount: int,
    grant: Optional[FreeGrant] = None,
    device: Optional[DeviceFingerprint] = None
) -> Tuple[bool, str]:
    """
    Проверить и списать токены у гостя.

    Возвращает: (success, error_message)

    ЖЕЛЕЗНАЯ ЛОГИКА:
    - Если нет токенов = НЕТ ГЕНЕРАЦИИ
    - Если устройство заблокировано = НЕТ ГЕНЕРАЦИИ
    - Списание атомарное с блокировкой
    """
    if amount <= 0:
        return True, ""

    # Получаем грант и устройство если не переданы
    if not grant or not device:
        grant, device, error = ensure_guest_grant_with_security(request)
        if error:
            return False, error
        if not grant:
            return False, "Не удалось получить грант"

    # Проверка блокировки устройства
    can_get, reason = device.can_get_tokens()
    if not can_get:
        return False, reason

    # Проверка наличия токенов
    if grant.left < amount:
        return False, f"Недостаточно токенов. Доступно: {grant.left}, требуется: {amount}"

    # Атомарное списание с блокировкой
    with transaction.atomic():
        # Перезагружаем грант с блокировкой
        locked_grant = FreeGrant.objects.select_for_update().get(pk=grant.pk)

        # Повторная проверка после блокировки
        if locked_grant.left < amount:
            return False, f"Недостаточно токенов. Доступно: {locked_grant.left}, требуется: {amount}"

        # Списываем токены
        spent = locked_grant.spend(amount)
        if spent != amount:
            return False, f"Не удалось списать токены. Списано: {spent}, требовалось: {amount}"

    log.info(f"Spent {amount} tokens from grant {grant.pk} for device {device.pk}")
    return True, ""


def get_guest_tokens_info(request: HttpRequest) -> dict:
    """
    Получить информацию о токенах гостя для отображения в UI.

    Возвращает:
    {
        'total': int,
        'consumed': int,
        'left': int,
        'is_blocked': bool,
        'block_reason': str,
        'can_generate': bool
    }
    """
    try:
        grant, device, error = ensure_guest_grant_with_security(request)

        if error or not grant or not device:
            return {
                'total': 0,
                'consumed': 0,
                'left': 0,
                'is_blocked': True,
                'block_reason': error or 'Не удалось получить информацию',
                'can_generate': False
            }

        can_get, reason = device.can_get_tokens()

        return {
            'total': grant.total,
            'consumed': grant.consumed,
            'left': grant.left,
            'is_blocked': not can_get,
            'block_reason': reason,
            'can_generate': can_get and grant.left > 0
        }
    except Exception as e:
        log.error(f"Error getting guest tokens info: {e}")
        return {
            'total': 0,
            'consumed': 0,
            'left': 0,
            'is_blocked': True,
            'block_reason': 'Ошибка системы',
            'can_generate': False
        }
