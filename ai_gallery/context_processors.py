# FILE: ai_gallery/context_processors.py
from django.conf import settings


def auth_flags(request):
    google = bool(
        getattr(settings, "GOOGLE_CLIENT_ID", None)
        and getattr(settings, "GOOGLE_CLIENT_SECRET", None)
    )
    facebook = bool(
        getattr(settings, "FACEBOOK_CLIENT_ID", None)
        and getattr(settings, "FACEBOOK_CLIENT_SECRET", None)
    )
    discord = bool(
        getattr(settings, "DISCORD_CLIENT_ID", None)
        and getattr(settings, "DISCORD_CLIENT_SECRET", None)
    )
    return {
        "GOOGLE_ENABLED": google,
        "FACEBOOK_ENABLED": facebook,
        "DISCORD_ENABLED": discord,
        "ANY_SOCIAL_ENABLED": google or facebook or discord,
        "DEFAULT_THEME": getattr(settings, "DEFAULT_THEME", "dark"),
    }


def wallet_context(request):
    """
    Универсальный контекст баланса:
    - token_cost (alias: price)
    - guest_initial
    - wallet_balance (для авторизованного)
    - guest_balance (для гостя) + alias guest_tokens
    - SUPPORT_TELEGRAM_URL
    """
    token_cost = int(getattr(settings, "TOKEN_COST_PER_GEN", 10))
    guest_initial = int(getattr(settings, "GUEST_INITIAL_TOKENS", 30))

    out = {
        "token_cost": token_cost,
        "price": token_cost,  # совместимость со старыми шаблонами
        "guest_initial": guest_initial,
        "wallet_balance": None,
        "guest_balance": None,
        "guest_tokens": None,  # alias для шаблонов
        "SUPPORT_TELEGRAM_URL": getattr(settings, "SUPPORT_TELEGRAM_URL", ""),
    }

    user = getattr(request, "user", None)
    if user and user.is_authenticated and hasattr(user, "wallet"):
        try:
            out["wallet_balance"] = int(user.wallet.balance or 0)
        except Exception:
            out["wallet_balance"] = 0
    else:
        used = int(request.session.get("guest_used_gens", 0))
        left = max(guest_initial - used * token_cost, 0)
        out["guest_balance"] = left
        out["guest_tokens"] = left  # alias

    return out
