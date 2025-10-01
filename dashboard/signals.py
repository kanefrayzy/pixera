# FILE: dashboard/signals.py
from __future__ import annotations

import hashlib
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in

from .models import Wallet, STARTER_TOKENS

# Эти модели импортируем тут, чтобы избежать циклов при старте приложений
from generate.models import FreeGrant, GenerationJob

User = get_user_model()


@receiver(post_save, sender=User)
def create_wallet_for_user(sender, instance, created, **kwargs):
    """
    Создаём пустой кошелёк при регистрации пользователя.
    ВАЖНО: баланс = STARTER_TOKENS (0), чтобы не «возвращать» гостевые токены.
    """
    if created:
        Wallet.objects.get_or_create(user=instance, defaults={"balance": STARTER_TOKENS})


def _ua_hash(request) -> str:
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    al = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
    return hashlib.sha256(f"{ua}|{al}".encode("utf-8")).hexdigest()


def _ip_hash(request) -> str:
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or \
         (request.META.get("REMOTE_ADDR") or "")
    if not ip:
        return ""
    return hashlib.sha256(f"{ip}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()


def _hard_fp(request) -> str:
    return hashlib.sha256(f"{_ua_hash(request)}|{_ip_hash(request)}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """
    1) Переносим остаток гостевой квоты в Wallet и «обнуляем» гостя (однократно).
    2) Привязываем все гостевые GenerationJob текущей сессии к пользователю.
    """
    # гарантируем session_key (нужен для связи гостевых задач)
    if not request.session.session_key:
        request.session.save()

    # --- 1) Перенос гостевых токенов ---
    try:
        gid = (request.COOKIES.get("gid") or "").strip()
        grant = FreeGrant.ensure_for(
            fp=_hard_fp(request),
            gid=gid,
            session_key=request.session.session_key,
            ip_hash=_ip_hash(request),
            ua_hash=_ua_hash(request),
            first_ip=(request.META.get("REMOTE_ADDR") or "").strip() or None,
        )
        # если уже привязано к этому юзеру — переносить нечего
        if grant.user_id != user.id:
            grant.transfer_all_left_to_wallet(user)  # перенесёт left и сделает consumed=total
    except Exception:
        # не мешаем логину даже если что-то пошло не так
        pass

    # --- 2) Привязка гостевых работ текущей сессии к аккаунту ---
    try:
        with transaction.atomic():
            GenerationJob.objects.select_for_update() \
                .filter(user__isnull=True, guest_session_key=request.session.session_key) \
                .update(user=user, guest_session_key="")
    except Exception:
        pass
