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

        # 1) пробуем ?next=
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url

        # 2) пусть решит адаптер allauth (учтёт ACCOUNT_LOGIN_ON_SIGNUP и т.п.)
        try:
            return get_adapter(request).get_login_redirect_url(request)
        except Exception:
            pass

        # 3) запасной вариант из настроек
        fallback = getattr(settings, "ACCOUNT_SIGNUP_REDIRECT_URL", None) or \
                   getattr(settings, "LOGIN_REDIRECT_URL", "/")
        # resolve_url сохраняет query (?drawer=1) если он указан строкой
        return resolve_url(fallback)
