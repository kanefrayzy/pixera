from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf.urls.i18n import set_language, i18n_patterns

from ai_gallery.views_auth import InstantSignupView

# Без языкового префикса
urlpatterns = [
    path("i18n/setlang/", set_language, name="set_language"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]

# С языковым префиксом (русский — язык по умолчанию БЕЗ префикса)
urlpatterns += i18n_patterns(
    # allauth под префиксом (чтобы /en/accounts/login/ работал)
    path("accounts/signup/", InstantSignupView.as_view(), name="account_signup"),
    path("accounts/", include("allauth.urls")),

    # приложения
    path("", include(("pages.urls", "pages"), namespace="pages")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("gallery/", include(("gallery.urls", "gallery"), namespace="gallery")),
    path("generate/", include(("generate.urls", "generate"), namespace="generate")),
    path("blog/", include(("blog.urls", "blog"), namespace="blog")),

    prefix_default_language=False,  # ru без /ru/, остальные с префиксом
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Preview 404 page in development
    urlpatterns += [path("dev/404/", TemplateView.as_view(template_name="404.html"))]
    # Preview 400 page in development
    urlpatterns += [path("dev/400/", TemplateView.as_view(template_name="404.html"))]

# Custom error handlers
def error_404(request, exception, template_name="404.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=404)
    # SEO: запрет индексации 404 страниц и корректная обработка любыми парсерами
    response["X-Robots-Tag"] = "noindex, follow"
    return response

handler404 = "ai_gallery.urls.error_404"

def error_400(request, exception, template_name="404.html"):
    from django.shortcuts import render
    response = render(request, template_name, status=400)
    response["X-Robots-Tag"] = "noindex, follow"
    return response

handler400 = "ai_gallery.urls.error_400"
