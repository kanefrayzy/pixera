from pages.models import SiteSettings


def site_settings(request):
    """
    Context processor для настроек сайта
    """
    try:
        settings = SiteSettings.get_settings()
        return {
            'site_settings': settings,
        }
    except Exception:
        return {
            'site_settings': None,
        }
