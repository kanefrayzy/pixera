# ai_gallery/views_auth.py
from __future__ import annotations

from django.conf import settings
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from allauth.account.views import SignupView
from allauth.account.adapter import get_adapter


class InstantSignupView(SignupView):
    """
    Кастомная signup-вьюха, совместимая с django-allauth.
    Делает безопасный редирект: ?next= (если свой хост) -> адаптер allauth -> настройки.
    """

    def get_success_url(self):
        request = self.request

        # Всегда ведём на профиль через адаптер; игнорируем ?next=
        try:
            return get_adapter(request).get_login_redirect_url(request)
        except Exception:
            pass

        # Фолбэк на настройки (по умолчанию — профиль)
        fallback = getattr(settings, "ACCOUNT_SIGNUP_REDIRECT_URL", None) or getattr(settings, "LOGIN_REDIRECT_URL", "/dashboard/me")
        return resolve_url(fallback)
