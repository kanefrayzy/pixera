from __future__ import annotations

from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter


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
