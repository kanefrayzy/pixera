from __future__ import annotations

from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """
    Custom allauth adapter that always redirects to the user's profile layout
    after login and after signup, ignoring any ?next= parameters.
    """

    def get_login_redirect_url(self, request):
        # Prefer named URL; fallback to settings or hardcoded path
        try:
            target = reverse("dashboard:me")
        except Exception:
            target = getattr(settings, "LOGIN_REDIRECT_URL", "/dashboard/me")
        return resolve_url(target)

    def get_signup_redirect_url(self, request):
        # Keep behavior consistent with login redirect
        return self.get_login_redirect_url(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for automatic username generation
    """

    def is_auto_signup_allowed(self, request, sociallogin):
        # Всегда разрешаем автоматическую регистрацию
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Автоматически заполняем данные пользователя из социальной сети
        """
        user = super().populate_user(request, sociallogin, data)

        # Генерируем username из email или имени
        if not user.username:
            email = data.get('email', '')
            name = data.get('name', '')
            first_name = data.get('first_name', '')

            # Пробуем использовать часть email до @
            if email:
                base_username = email.split('@')[0]
            elif name:
                base_username = name.replace(' ', '_').lower()
            elif first_name:
                base_username = first_name.lower()
            else:
                base_username = f'user{sociallogin.account.uid[:8]}'

            # Очищаем от недопустимых символов
            import re
            base_username = re.sub(r'[^\w.@+-]', '_', base_username)

            # Проверяем уникальность и добавляем номер при необходимости
            from django.contrib.auth import get_user_model
            User = get_user_model()
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user.username = username

        return user
