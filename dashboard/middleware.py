# FILE: dashboard/middleware.py
from __future__ import annotations

from typing import Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .models import Wallet

# Можно задать STARTER_TOKENS в settings; иначе возьмём 0 (или GUEST_INITIAL_TOKENS, если задан)
STARTER_TOKENS_FALLBACK = getattr(
    settings, "STARTER_TOKENS", getattr(settings, "GUEST_INITIAL_TOKENS", 0)
)


class EnsureWalletMiddleware:
    """
    Гарантирует, что у авторизованного пользователя есть Wallet.
    Делает get_or_create один раз за сессию (чтобы не трогать БД на каждый запрос).
    Для гостей ничего не делает.
    """

    _SESSION_FLAG = "_wallet_ready"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)

        if user and user.is_authenticated and not request.session.get(self._SESSION_FLAG):
            try:
                # Проверяем, есть ли уже кошелек у пользователя
                wallet, created = Wallet.objects.get_or_create(
                    user=user,
                    # ВАЖНО: стартовый баланс только при создании, существующие кошельки не трогаем
                    defaults={
                        "balance": int(STARTER_TOKENS_FALLBACK) or 0,
                        "purchased_total": 0,
                    },
                )
                # Если кошелек уже существовал, не добавляем токены повторно
            except Exception:
                # Не блокируем пайплайн из-за ошибок кошелька
                pass
            else:
                # Отметим, чтобы в этой сессии больше не дергать БД
                request.session[self._SESSION_FLAG] = True

        return self.get_response(request)
