# FILE: dashboard/urls.py
from django.urls import path, include
from django.views.generic import RedirectView
from . import views

app_name = "dashboard"

urlpatterns = [
    # Кабинет
    path("", views.index, name="index"),
    path("my-jobs", views.my_jobs, name="my_jobs"),
    path("tips", views.tips, name="tips"),

    # Баланс и пополнение
    path("balance", views.balance, name="balance"),
    path("tariffs", views.tariffs, name="tariffs"),

    # Покупка тарифа (флоу)
    path("purchase/<slug:plan_id>", views.purchase_start, name="purchase_start"),
    path("purchase/<slug:plan_id>/checkout", views.purchase_checkout, name="purchase_checkout"),
    path("purchase/<slug:plan_id>/pay", views.purchase_pay, name="purchase_pay"),

    # Управление примерами слайдера
    path("slider-examples/", include("gallery.urls_slider", namespace="slider")),

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
]
