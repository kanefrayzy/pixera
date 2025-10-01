# FILE: generate/urls.py
from django.urls import path, re_path

from . import views, views_api

app_name = "generate"

urlpatterns = [
    # ── Страница генерации
    path("new/", views.new, name="new"),

    # ── API генерации
    path("api/submit/", views_api.api_submit, name="api_submit"),
    path("api/status/<int:job_id>/", views_api.api_status, name="api_status"),
    path("api/runware/webhook/", views_api.runware_webhook, name="runware_webhook"),

    # ── CRUD подсказок (staff)
    path("api/suggestions/create/", views.api_suggestion_create, name="api_suggestion_create"),
    path("api/suggestions/<int:pk>/update/", views.api_suggestion_update, name="api_suggestion_update"),
    path("api/suggestions/<int:pk>/delete/", views.api_suggestion_delete, name="api_suggestion_delete"),

    # ── CRUD категорий подсказок (staff)
    path("api/suggestion-categories/create/", views_api.cat_create, name="api_cat_create"),
    path("api/suggestion-categories/<int:pk>/update/", views_api.cat_update, name="api_cat_update"),
    path("api/suggestion-categories/<int:pk>/delete/", views_api.cat_delete, name="api_cat_delete"),

    # ── Удаление (GET подтверждение / POST действие) — обязательно выше slug-маршрутов
    path("job/<int:pk>/delete/", views.job_confirm_delete, name="job_confirm_delete"),
    path("job/<int:pk>/delete/confirm/", views.job_delete, name="job_delete"),

    # ── Спец-роуты задачи — также выше общего slug
    path("job/<int:pk>/<slug:slug>/status/", views.job_status, name="job_status"),
    path("job/<int:pk>/status/", views.job_status_no_slug, name="job_status_no_slug"),
    path("job/<int:pk>/<slug:slug>/image/", views.job_image, name="job_image"),

    # ── Детали задачи без слага → редирект на канонический
    path("job/<int:pk>/", views.job_detail_no_slug, name="job_detail_no_slug"),

    # ── Мои работы
    path("my/", views.my_jobs_all, name="my_jobs"),
    path("api/guest-balance/", views_api.guest_balance, name="api_guest_balance"),

    # ── Детали задачи (общий slug-роут).
    # Негативный lookahead защищает от конфликтов со спец-суффиксами (delete/status/image).
    re_path(
        r"^job/(?P<pk>\d+)/(?!(?:delete|status|image)/?$)(?P<slug>[-\w]+)/$",
        views.job_detail,
        name="job_detail",
    ),
]
