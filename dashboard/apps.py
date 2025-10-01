# FILE: dashboard/apps.py
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"

    def ready(self):
        # Регистрируем сигналы после загрузки всех приложений.
        from . import signals  # noqa: F401
