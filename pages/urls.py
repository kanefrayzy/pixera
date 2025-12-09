from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),              # ← корень сайта
    path("about", views.about, name="about"),
    path("contact", views.contact, name="contact"),
    path("privacy", views.privacy, name="privacy"),
    path("age/accept", views.age_accept, name="age_accept"),
    path("robots.txt", views.RobotsView.as_view(), name="robots"),

    # Legacy redirects
    path("about/", RedirectView.as_view(pattern_name="pages:about", permanent=True)),
    path("contact/", RedirectView.as_view(pattern_name="pages:contact", permanent=True)),
    path("privacy/", RedirectView.as_view(pattern_name="pages:privacy", permanent=True)),
    path("age/accept/", RedirectView.as_view(pattern_name="pages:age_accept", permanent=True)),
]
