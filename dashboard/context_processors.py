# FILE: dashboard/context_processors.py
from __future__ import annotations

import hashlib
from django.conf import settings
from dashboard.models import Wallet

# будем лениво подтягивать FreeGrant, чтобы избежать циклических импортов при старте
def _ensure_free_grant_for(request):
    """Возвращает или создаёт FreeGrant, аккуратно учитывая fp/gid/session/ip/ua."""
    from generate.models import FreeGrant

    # session_key обязателен для надёжной привязки гостевых задач
    if not request.session.session_key:
        request.session.save()

    gid = (request.COOKIES.get("gid") or "").strip()

    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()
    al = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").strip()
    ua_hash = hashlib.sha256(f"{ua}|{al}".encode("utf-8")).hexdigest()

    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip() or \
         (request.META.get("REMOTE_ADDR") or "")
    ip_hash = hashlib.sha256(f"{ip}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest() if ip else ""

    hard_fp = hashlib.sha256(f"{ua_hash}|{ip_hash}|{settings.SECRET_KEY}".encode("utf-8")).hexdigest()

    return FreeGrant.ensure_for(
        fp=hard_fp,
        gid=gid,
        session_key=request.session.session_key,
        ip_hash=ip_hash,
        ua_hash=ua_hash,
        first_ip=ip or None,
    )

def _price_for_user(user) -> int:
    """0 — если staff и FREE_FOR_STAFF, иначе TOKEN_COST."""
    token_cost = int(getattr(settings, "TOKEN_COST_PER_GEN", 10))
    free_for_staff = bool(getattr(settings, "FREE_FOR_STAFF", True))
    if user and user.is_authenticated and (user.is_staff or user.is_superuser) and free_for_staff:
        return 0
    return token_cost

def wallet_context(request):
    """
    Добавляет в контекст:
      - wallet (объект кошелька)
      - wallet_leftover (баланс в токенах)
      - is_free_for_staff (флаг безлимита для стаффа)
      - price_per_gen (стоимость одной генерации)
      - gens_left (сколько генераций доступно по текущей цене)
    И *однократно за сессию* переносит остаток гостевой квоты в кошелёк.
    """
    if not request.user.is_authenticated:
        return {}

    # 1) гарантируем кошелёк
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # 2) один раз за сессию переносим остаток гостя
    try:
        session_key = f"grant_merged_once_{request.user.id}"
        if not request.session.get(session_key):
            # Проверяем, есть ли уже привязанный к этому пользователю FreeGrant
            from generate.models import FreeGrant
            existing_grant = FreeGrant.objects.filter(user=request.user).first()
            if existing_grant:
                # У пользователя уже есть привязанный грант, не создаем новый и не переносим токены
                pass
            else:
                grant = _ensure_free_grant_for(request)
                # если эта гостевая запись ещё не принадлежит этому юзеру — перенесём остаток
                if grant.user_id != request.user.id:
                    grant.bind_to_user(request.user, transfer_left=True)
            request.session[session_key] = True
            request.session.modified = True
    except Exception:
        pass

    # 3) расчёт стоимости и оставшихся генераций
    price = _price_for_user(request.user)
    gens_left = 0 if price == 0 else (int(wallet.balance or 0) // max(1, price))
    is_free_for_staff = (price == 0)

    return {
        "wallet": wallet,
        "wallet_leftover": wallet.balance,
        "is_free_for_staff": is_free_for_staff,
        "price_per_gen": price,
        "gens_left": gens_left,
    }


def user_profile(request):
    """
    Гарантированно добавляет в контекст профиль пользователя (для аватарки).
    Безопасно создаёт профиль при первом обращении.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"user_profile": None}
    try:
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=user)
    except Exception:
        profile = None
    return {"user_profile": profile}


def follow_stats(request):
    """
    Добавляет в контекст счётчики подписчиков/подписок/публикаций для текущего пользователя.
    Публикации считаем как все завершенные работы (GenerationJob.DONE).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    try:
        from .models import Follow
        followers = Follow.objects.filter(following=user).count()
        following = Follow.objects.filter(follower=user).count()
    except Exception:
        followers = 0
        following = 0

    posts = 0
    try:
        from generate.models import GenerationJob
        posts = GenerationJob.objects.filter(user=user, status=GenerationJob.Status.DONE).filter(persisted=True).count()
    except Exception:
        pass

    return {"follow_stats": {"followers": followers, "following": following, "posts": posts}}
