# gallery/urls.py
from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "gallery"

urlpatterns = [
    # Лента
    path("", views.index, name="index"),

    # Тренды — каноничный URL со слэшем
    path("trending/", views.trending, name="trending"),
    # HTML-фрагмент для главной: подгрузка сетки «Тренд/Новые» без перехода
    path("trending/snippet/", views.trending_snippet, name="trending_snippet"),
    # Алиас на русский
    path("populyarnoe/", RedirectView.as_view(pattern_name="gallery:trending", permanent=True), name="trending_legacy"),

    # Легаси/без слэша → 301 на каноничный (чтобы не было дубликатов и 404)
    path("trending",    RedirectView.as_view(pattern_name="gallery:trending",    permanent=True)),
    path("populyarnoe", RedirectView.as_view(pattern_name="gallery:trending",    permanent=True)),

    # Фото и действия
    path("photo/<int:pk>/", views.photo_detail,  name="photo_detail"),
    path("photo/<int:pk>/like/",    views.photo_like,    name="photo_like"),
    path("photo/<int:pk>/comment/", views.photo_comment, name="photo_comment"),

    # Комментарии: лайк и ответ
    path("comment/<int:pk>/like/",  views.comment_like,  name="comment_like"),
    path("comment/<int:pk>/reply/", views.comment_reply, name="comment_reply"),

    # Поделиться из генерации
    path("share/<int:job_id>/", views.share_from_job, name="share_from_job"),

    # Удаление генерации из «Моих работ» (view в gallery.views)
    path("job/<int:pk>/delete/", views.job_delete, name="job_delete"),

    # Редактирование/удаление публичной публикации (только для staff)
    path("photo/<int:pk>/edit/",   views.photo_edit,   name="photo_edit"),
    path("photo/<int:pk>/delete/", views.photo_delete, name="photo_delete"),

    # Модерация (только для staff)
    path("moderation/",                    views.moderation,          name="moderation"),
    path("moderation/<int:pk>/approve/",  views.moderation_approve,  name="moderation_approve"),
    path("moderation/<int:pk>/reject/",   views.moderation_reject,   name="moderation_reject"),

    # Admin-утилиты (алиасы на staff-вьюхи)
    path("admin/category/add/",                 views.admin_category_add,  name="admin_category_add"),
    path("admin/public/add/",                   views.admin_public_add,    name="admin_public_add"),
    path("admin/public/<int:pk>/delete/",       views.admin_public_delete, name="admin_public_delete"),
]
