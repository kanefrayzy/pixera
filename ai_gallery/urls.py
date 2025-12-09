from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf.urls.i18n import set_language, i18n_patterns
from dashboard import views as dashboard_views
from pages.health import HealthCheckView

from ai_gallery.views_auth import InstantSignupView

# Без языкового префикса
urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("i18n/setlang/", set_language, name="set_language"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

# С языковым префиксом (русский — язык по умолчанию БЕЗ префикса)
urlpatterns += i18n_patterns(
    # allauth под префиксом (чтобы /en/accounts/login/ работал)
    path("accounts/signup/", InstantSignupView.as_view(), name="account_signup"),
    path("accounts/", include("allauth.urls")),
    path("profile-<str:username>", dashboard_views.profile, name="profile_short"),

    # приложения
    path("", include(("pages.urls", "pages"), namespace="pages")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("gallery/", include(("gallery.urls", "gallery"), namespace="gallery")),
    path("generate/", include(("generate.urls", "generate"), namespace="generate")),
    path("blog/", include(("blog.urls", "blog"), namespace="blog")),

    prefix_default_language=False,  # ru без /ru/, остальные с префиксом
)

# Sitemap configuration
from django.contrib.sitemaps.views import sitemap

try:
    from pages.sitemaps import StaticViewSitemap, PagesSitemap
    from gallery.sitemaps import GallerySitemap
    from blog.sitemaps import BlogSitemap

    sitemaps = {
        'static': StaticViewSitemap,
        'pages': PagesSitemap,
        'gallery': GallerySitemap,
        'blog': BlogSitemap,
    }
except ImportError:
    # Fallback если какие-то sitemap отсутствуют
    from pages.sitemaps import StaticViewSitemap
    sitemaps = {
        'static': StaticViewSitemap,
    }

urlpatterns += [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    # Serve static files from STATICFILES_DIRS in development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Preview 404 page in development
    urlpatterns += [path("dev/404/", TemplateView.as_view(template_name="404.html"))]
    # Preview 400 page in development
    urlpatterns += [path("dev/400/", TemplateView.as_view(template_name="404.html"))]

# Custom error handlers
def error_404(request, exception, template_name="404.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=404)
    response["X-Robots-Tag"] = "noindex, follow"
    return response

def error_500(request, template_name="500.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=500)
    response["X-Robots-Tag"] = "noindex, follow"
    return response

def error_403(request, exception, template_name="403.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=403)
    response["X-Robots-Tag"] = "noindex, follow"
    return response

def error_400(request, exception, template_name="400.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=400)
    response["X-Robots-Tag"] = "noindex, follow"
    return response

handler404 = "ai_gallery.urls.error_404"
handler500 = "ai_gallery.urls.error_500"
handler403 = "ai_gallery.urls.error_403"
handler400 = "ai_gallery.urls.error_400"
