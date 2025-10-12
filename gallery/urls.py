# gallery/urls.py
from __future__ import annotations

from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import views_video

app_name = "gallery"

urlpatterns = [
    # Лента
    path("", views.index, name="index"),

    # Тренды — каноничный URL без слэша
    path("trending", views.trending, name="trending"),
    # HTML-фрагмент для главной: подгрузка сетки «Тренд/Новые» без перехода
    path("trending/snippet", views.trending_snippet, name="trending_snippet"),
    # Алиас на русский
    path("populyarnoe", RedirectView.as_view(pattern_name="gallery:trending", permanent=True), name="trending_legacy"),

    # Legacy redirects
    path("trending/", RedirectView.as_view(pattern_name="gallery:trending", permanent=True)),
    path("populyarnoe/", RedirectView.as_view(pattern_name="gallery:trending", permanent=True)),
    path("trending/snippet/", RedirectView.as_view(pattern_name="gallery:trending_snippet", permanent=True)),

    # Фото и действия
    path("photo/<int:pk>", views.photo_detail,  name="photo_detail"),
    path("photo/<int:pk>/like",    views.photo_like,    name="photo_like"),
    path("photo/<int:pk>/comment", views.photo_comment, name="photo_comment"),

    # Комментарии: лайк и ответ
    path("comment/<int:pk>/like",  views.comment_like,  name="comment_like"),
    path("comment/<int:pk>/reply", views.comment_reply, name="comment_reply"),

    # Поделиться из генерации
    path("share/<int:job_id>", views.share_from_job, name="share_from_job"),

    # Удаление генерации из «Моих работ» (view в gallery.views)
    path("job/<int:pk>/delete", views.job_delete, name="job_delete"),

    # Редактирование/удаление публичной публикации (только для staff)
    path("photo/<int:pk>/edit",   views.photo_edit,   name="photo_edit"),
    path("photo/<int:pk>/delete", views.photo_delete, name="photo_delete"),

    # Модерация (только для staff)
    path("moderation",                    views.moderation,          name="moderation"),
    path("moderation/<int:pk>/approve",  views.moderation_approve,  name="moderation_approve"),
    path("moderation/<int:pk>/reject",   views.moderation_reject,   name="moderation_reject"),

    # Видео и действия
    path("video/<int:pk>", views_video.video_detail, name="video_detail"),
    path("video/<int:pk>/like", views_video.video_like, name="video_like"),
    path("video/<int:pk>/comment", views_video.video_comment, name="video_comment"),

    # Комментарии к видео
    path("video-comment/<int:pk>/like", views_video.video_comment_like, name="video_comment_like"),
    path("video-comment/<int:pk>/reply", views_video.video_comment_reply, name="video_comment_reply"),

    # Поделиться видео из генерации
    path("share-video/<int:job_id>", views_video.share_video_from_job, name="share_video_from_job"),

    # Удаление видео (только staff)
    path("video/<int:pk>/delete", views_video.video_delete, name="video_delete"),

    # Модерация видео (только staff)
    path("moderation/video/<int:pk>/approve", views_video.moderation_approve_video, name="moderation_approve_video"),
    path("moderation/video/<int:pk>/reject", views_video.moderation_reject_video, name="moderation_reject_video"),

    # Admin-утилиты (алиасы на staff-вьюхи)
    path("admin/category/add",                 views.admin_category_add,  name="admin_category_add"),

    # Legacy URL redirects
    path("photo/<int:pk>/", RedirectView.as_view(pattern_name="gallery:photo_detail", permanent=True)),
    path("photo/<int:pk>/like/", RedirectView.as_view(pattern_name="gallery:photo_like", permanent=True)),
    path("photo/<int:pk>/comment/", RedirectView.as_view(pattern_name="gallery:photo_comment", permanent=True)),
    path("comment/<int:pk>/like/", RedirectView.as_view(pattern_name="gallery:comment_like", permanent=True)),
    path("comment/<int:pk>/reply/", RedirectView.as_view(pattern_name="gallery:comment_reply", permanent=True)),
    path("share/<int:job_id>/", RedirectView.as_view(pattern_name="gallery:share_from_job", permanent=True)),
    path("job/<int:pk>/delete/", RedirectView.as_view(pattern_name="gallery:job_delete", permanent=True)),
    path("photo/<int:pk>/edit/", RedirectView.as_view(pattern_name="gallery:photo_edit", permanent=True)),
    path("photo/<int:pk>/delete/", RedirectView.as_view(pattern_name="gallery:photo_delete", permanent=True)),
    path("moderation/", RedirectView.as_view(pattern_name="gallery:moderation", permanent=True)),
    path("moderation/<int:pk>/approve/", RedirectView.as_view(pattern_name="gallery:moderation_approve", permanent=True)),
    path("moderation/<int:pk>/reject/", RedirectView.as_view(pattern_name="gallery:moderation_reject", permanent=True)),
    path("admin/category/add/", RedirectView.as_view(pattern_name="gallery:admin_category_add", permanent=True)),
    path("admin/public/add/",                   views.admin_public_add,    name="admin_public_add"),
    path("admin/public/<int:pk>/delete/",       views.admin_public_delete, name="admin_public_delete"),
]
