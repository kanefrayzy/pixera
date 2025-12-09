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
    """
    return {
        'fp': getattr(request, 'device_fp', ''),
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
    ЖЕЛЕЗНАЯ ЛОГИКА получения/создания гранта для гостя.

    Возвращает: (grant, device, error_message)

    4-ЭТАПНАЯ ЗАЩИТА:
    1. Проверка по FP (жёсткий отпечаток браузера)
    2. Проверка по GID (стойкий cookie)
    3. Проверка по IP hash (защита от VPN)
    4. Проверка по UA hash (отпечаток User-Agent)

    ПРАВИЛА:
    - Если найдено устройство с такими же GID+IP+UA но другим FP = ИНКОГНИТО
    - Если устройство заблокировано = НЕТ ДОСТУПА
    - Если токены закончились = НЕТ ДОСТУПА
    - Новое устройство = НОВЫЙ ГРАНТ с 30 токенами
    """
    ids = get_device_identifiers(request)

    fp = ids['fp']
    gid = ids['gid']
    ip_hash = ids['ip_hash']
    ua_hash = ids['ua_hash']
    session_key = ids['session_key']
    first_ip = ids['first_ip']

    # Кластерный идентификатор посетителя (объединяем разные браузеры/режимы)
    try:
        cluster = AbuseCluster.ensure_for(
            fp=fp, gid=gid, ip_hash=ip_hash, ua_hash=ua_hash
        )
    except Exception as e:
        log.error(f"Error ensuring cluster: {e}")
        cluster = None

    # Валидация: FP обязателен
    if not fp:
        log.error("FP is missing - cannot track device")
        return None, None, "Ошибка идентификации устройства"

    # Шаг 1: Получить или создать устройство с проверкой на обход
    try:
        device, created = DeviceFingerprint.get_or_create_device(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            first_ip=first_ip,
            session_key=session_key
        )
    except Exception as e:
        log.error(f"Error creating device: {e}")
        return None, None, "Ошибка системы безопасности"

    # Шаг 2: Проверка блокировки устройства
    can_get, reason = device.can_get_tokens()
    if not can_get:
        # Логируем заблокированную попытку
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

    # Шаг 3: Получить или создать грант
    if device.free_grant:
        # Устройство уже имеет грант
        grant = device.free_grant

        # Проверка: если грант привязан к пользователю - это ошибка
        if grant.is_bound_to_user:
            log.warning(f"Device {device.pk} has user-bound grant {grant.pk}")
            return None, device, "Грант уже привязан к пользователю"

        # Логируем успешный доступ к существующему гранту
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

        return grant, device, ""

    # Шаг 4: Создать новый грант для нового устройства
    if created:
        # Кластер: если уже есть грант в кластере — не создаём новый, а привязываем
        cluster_grant = _find_cluster_grant(cluster) if cluster else None
        if cluster_grant:
            if cluster_grant.is_bound_to_user:
                TokenGrantAttempt.objects.create(
                    fp=fp,
                    gid=gid,
                    ip_hash=ip_hash,
                    ua_hash=ua_hash,
                    session_key=session_key,
                    ip_address=first_ip,
                    was_granted=False,
                    was_blocked=True,
                    block_reason='Кластер: существующий грант уже привязан к пользователю',
                    device=device
                )
                return None, device, 'Грант уже привязан к пользователю'

            device.free_grant = cluster_grant
            device.save(update_fields=['free_grant', 'updated_at'])

            TokenGrantAttempt.objects.create(
                fp=fp,
                gid=gid,
                ip_hash=ip_hash,
                ua_hash=ua_hash,
                session_key=session_key,
                ip_address=first_ip,
                was_granted=True,
                was_blocked=False,
                block_reason='Кластер: найден и привязан существующий грант',
                device=device
            )
            return cluster_grant, device, ""

        # Это действительно новое устройство - даём токены
        grant = FreeGrant.objects.create(
            fp=fp,
            gid=gid,
            ua_hash=ua_hash,
            ip_hash=ip_hash,
            first_ip=first_ip,
            total=30,  # СТРОГО 30 токенов
            consumed=0
        )

        # Привязываем грант к устройству
        device.free_grant = grant
        device.save(update_fields=['free_grant', 'updated_at'])

        # Логируем выдачу новых токенов
        TokenGrantAttempt.objects.create(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            session_key=session_key,
            ip_address=first_ip,
            was_granted=True,
            was_blocked=False,
            block_reason='Новое устройство - выданы токены',
            device=device
        )

        log.info(f"Created new grant {grant.pk} for device {device.pk}")
        return grant, device, ""

    # Устройство существует но без гранта - ищем старый грант
    # Это может быть после миграции или если связь была разорвана
    # Сначала ищем грант в кластере (объединяет другие браузеры/инкогнито)
    cluster_grant = _find_cluster_grant(cluster) if cluster else None
    if cluster_grant:
        if cluster_grant.is_bound_to_user:
            TokenGrantAttempt.objects.create(
                fp=fp,
                gid=gid,
                ip_hash=ip_hash,
                ua_hash=ua_hash,
                session_key=session_key,
                ip_address=first_ip,
                was_granted=False,
                was_blocked=True,
                block_reason='Кластер: грант уже привязан к пользователю',
                device=device
            )
            return None, device, 'Грант уже привязан к пользователю'

        device.free_grant = cluster_grant
        device.save(update_fields=['free_grant', 'updated_at'])

        TokenGrantAttempt.objects.create(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            session_key=session_key,
            ip_address=first_ip,
            was_granted=True,
            was_blocked=False,
            block_reason='Кластер: восстановлена связь с существующим грантом',
            device=device
        )
        return cluster_grant, device, ""

    grant = FreeGrant.objects.filter(
        fp=fp,
        user__isnull=True
    ).first()

    if not grant:
        # Ищем по другим идентификаторам
        from django.db.models import Q
        grant = FreeGrant.objects.filter(
            Q(gid=gid) | Q(ip_hash=ip_hash),
            user__isnull=True
        ).first()

    if grant:
        # Нашли старый грант - привязываем к устройству
        device.free_grant = grant
        device.save(update_fields=['free_grant', 'updated_at'])

        TokenGrantAttempt.objects.create(
            fp=fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            session_key=session_key,
            ip_address=first_ip,
            was_granted=True,
            was_blocked=False,
            block_reason='Восстановлена связь с грантом',
            device=device
        )

        return grant, device, ""

    # Грант не найден - это подозрительно для существующего устройства
    # Возможно попытка обхода - НЕ ДАЁМ новые токены
    device.record_bypass_attempt("Попытка получить новый грант для существующего устройства")

    TokenGrantAttempt.objects.create(
        fp=fp,
        gid=gid,
        ip_hash=ip_hash,
        ua_hash=ua_hash,
        session_key=session_key,
        ip_address=first_ip,
        was_granted=False,
        was_blocked=True,
        block_reason='Подозрение на обход: устройство без гранта',
        device=device
    )

    return None, device, "Токены уже использованы"


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
