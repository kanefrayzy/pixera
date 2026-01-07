from django.urls import path
from django.views.generic import RedirectView
from django.views.static import serve
from django.conf import settings
import os
from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),              # ← корень сайта
    path("about", views.about, name="about"),
    path("contact", views.contact, name="contact"),
    path("privacy", views.privacy, name="privacy"),
    path("age/accept", views.age_accept, name="age_accept"),
    # robots.txt
    path("robots.txt", lambda r: serve(r, 'robots.txt', document_root=settings.BASE_DIR), name="robots"),

    # Legacy redirects
    path("about/", RedirectView.as_view(pattern_name="pages:about", permanent=True)),
    path("contact/", RedirectView.as_view(pattern_name="pages:contact", permanent=True)),
    path("privacy/", RedirectView.as_view(pattern_name="pages:privacy", permanent=True)),
    path("age/accept/", RedirectView.as_view(pattern_name="pages:age_accept", permanent=True)),
]
