from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def nav_context(_request):
    try:
        return {
            "RUNWARE_ALLOWED_MODELS": getattr(settings, "RUNWARE_ALLOWED_MODELS", []),
            "RUNWARE_DEFAULT_MODEL": getattr(settings, "RUNWARE_DEFAULT_MODEL", ""),
        }
    except Exception as e:
        logger.error(f"Error in nav_context: {e}")
        return {
            "RUNWARE_ALLOWED_MODELS": [],
            "RUNWARE_DEFAULT_MODEL": "",
        }

