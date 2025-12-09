# FILE: dashboard/urls.py
from django.urls import path, include
from django.views.generic import RedirectView
from . import views

app_name = "dashboard"

urlpatterns = [
    # Кабинет
    path("", RedirectView.as_view(pattern_name="pages:home", permanent=True), name="index"),
    path("profile/<str:username>", RedirectView.as_view(pattern_name="profile_short", permanent=True), name="profile"),
    path("me", views.me, name="me"),
    path("my-jobs", views.my_jobs, name="my_jobs"),
    path("saved", views.saved, name="saved"),
    path("tips", views.tips, name="tips"),

    # Уведомления
    path("notifications", views.notifications_page, name="notifications"),
    path("publication-deleted", views.publication_deleted, name="publication_deleted"),

    # Баланс и пополнение
    path("balance", views.balance, name="balance"),
    path("tariffs", views.tariffs, name="tariffs"),

    # Покупка тарифа (флоу)
    path("purchase/<slug:plan_id>", views.purchase_start, name="purchase_start"),
    path("purchase/<slug:plan_id>/checkout", views.purchase_checkout, name="purchase_checkout"),
    path("purchase/<slug:plan_id>/pay", views.purchase_pay, name="purchase_pay"),

    # Управление примерами слайдера
    path("slider-examples/", include("gallery.urls_slider", namespace="slider")),

    # Аватар
    path("avatar/upload", views.avatar_upload, name="avatar_upload"),
    path("avatar/delete", views.avatar_delete, name="avatar_delete"),
    path("profile/privacy/toggle", views.toggle_profile_privacy, name="toggle_profile_privacy"),

    # API управление
    path("api/", include("dashboard.urls_api", namespace="api")),

    # Сервисные алиасы (совместимость с реверсами в коде)
    path(
        "billing",
        RedirectView.as_view(pattern_name="dashboard:tariffs", permanent=False),
        name="billing",
    ),
    path(
        "change_password",
        RedirectView.as_view(pattern_name="account_change_password", permanent=False),
        name="change_password",
    ),

    # Legacy redirects
]
