from django.conf import settings
def nav_context(_request):
    return {
        "RUNWARE_ALLOWED_MODELS": getattr(settings, "RUNWARE_ALLOWED_MODELS", []),
        "RUNWARE_DEFAULT_MODEL": getattr(settings, "RUNWARE_DEFAULT_MODEL", ""),
    }

