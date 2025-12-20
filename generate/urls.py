# FILE: generate/urls.py
from django.urls import path, re_path, include
from django.views.generic import RedirectView

from . import views, views_api, views_prompts_api, views_video_api, views_video_models, views_image_models
from . import views_queue_api

app_name = "generate"

urlpatterns = [
    # ── Страница генерации
    path("photo", views.new_photo, name="photo"),
    path("video", views.new_video, name="video"),
    path("new", views.new, name="new"),  # Старый URL для совместимости

    # ── Управление моделями изображений (admin only)
    path("admin/image-models", views_image_models.image_models_list, name="image_models_list"),
    path("admin/image-models/create", views_image_models.image_model_create, name="image_model_create"),
    path("admin/image-models/<int:pk>", views_image_models.image_model_detail, name="image_model_detail"),
    path("admin/image-models/<int:pk>/edit", views_image_models.image_model_edit, name="image_model_edit"),
    path("admin/image-models/<int:pk>/delete", views_image_models.image_model_delete, name="image_model_delete"),
    path("admin/image-models/<int:pk>/toggle-active", views_image_models.image_model_toggle_active, name="image_model_toggle_active"),
    path("admin/image-models/<int:pk>/duplicate", views_image_models.image_model_duplicate, name="image_model_duplicate"),

    # ── Управление видео моделями (admin only)
    path("admin/video-models", views_video_models.video_models_list, name="video_models_list"),
    path("admin/video-models/create", views_video_models.video_model_create, name="video_model_create"),
    path("admin/video-models/<int:pk>", views_video_models.video_model_detail, name="video_model_detail"),
    path("admin/video-models/<int:pk>/edit", views_video_models.video_model_edit, name="video_model_edit"),
    path("admin/video-models/<int:pk>/delete", views_video_models.video_model_delete, name="video_model_delete"),
    path("admin/video-models/<int:pk>/toggle-active", views_video_models.video_model_toggle_active, name="video_model_toggle_active"),
    path("admin/video-models/<int:pk>/duplicate", views_video_models.video_model_duplicate, name="video_model_duplicate"),
    path("admin/video-models/<int:pk>/quick-edit", views_video_models.video_model_quick_edit, name="video_model_quick_edit"),
    path("admin/video-models/bulk-action", views_video_models.video_model_bulk_action, name="video_model_bulk_action"),
    path("api/video-models/<int:pk>/config", views_video_models.video_model_api_config, name="video_model_api_config"),

    # ── Страница категорий промптов
    path("prompts", views.prompts_page, name="prompts"),

    # ── API генерации изображений
    path("api/submit", views_api.api_submit, name="api_submit"),
    path("api/status/<int:job_id>", views_api.api_status, name="api_status"),
    path("api/job/<int:pk>/persist", views_api.job_persist, name="api_job_persist"),
    path("api/last-pending", views_api.api_last_pending, name="api_last_pending"),
    path("api/completed-jobs", views_api.api_completed_jobs, name="api_completed_jobs"),
    # Очередь: удаление одного элемента и полной очереди (перманентно)
    path("api/queue/remove", views_queue_api.queue_remove, name="api_queue_remove"),
    path("api/queue/clear", views_queue_api.queue_clear, name="api_queue_clear"),
    path("api/prompt/ai", views_api.prompt_ai, name="api_prompt_ai"),
    path("api/runware/webhook", views_api.runware_webhook, name="runware_webhook"),

    # ── API генерации видео
    path("api/video/models", views_video_api.video_models_list, name="api_video_models"),
    path("api/video/submit", views_video_api.video_submit, name="api_video_submit"),
    path("api/video/status/<int:job_id>", views_video_api.video_status, name="api_video_status"),
    path("api/video/last-pending", views_video_api.video_last_pending, name="api_video_last_pending"),
    path("api/video/categories/<int:category_id>/prompts", views_video_api.video_category_prompts_api, name="api_video_category_prompts"),

    # ── API управления видео контентом (категории, промпты, showcase)
    path("", include("generate.urls_video_content")),

    # ── CRUD подсказок (staff)
    path("api/suggestions/create", views.api_suggestion_create, name="api_suggestion_create"),
    path("api/suggestions/<int:pk>/update", views.api_suggestion_update, name="api_suggestion_update"),
    path("api/suggestions/<int:pk>/delete", views.api_suggestion_delete, name="api_suggestion_delete"),

    # ── CRUD категорий подсказок (staff)
    path("api/suggestion-categories/create", views_api.cat_create, name="api_cat_create"),
    path("api/suggestion-categories/<int:pk>/update", views_api.cat_update, name="api_cat_update"),
    path("api/suggestion-categories/<int:pk>/delete", views_api.cat_delete, name="api_cat_delete"),

    # ── CRUD prompt categories (staff)
    path("api/prompt-categories/create", views_prompts_api.pc_create, name="api_pc_create"),
    path("api/prompt-categories/<int:pk>/update", views_prompts_api.pc_update, name="api_pc_update"),
    path("api/prompt-categories/<int:pk>/delete", views_prompts_api.pc_delete, name="api_pc_delete"),

    # ── CRUD category prompts (staff)
    path("api/prompts/create", views_prompts_api.cp_create, name="api_cp_create"),
    path("api/prompts/<int:pk>/update", views_prompts_api.cp_update, name="api_cp_update"),
    path("api/prompts/<int:pk>/delete", views_prompts_api.cp_delete, name="api_cp_delete"),

    # ── Подкатегории промптов (staff + public)
    path("api/subcategories/create", views_prompts_api.sc_create, name="api_sc_create"),
    path("api/subcategories/<int:pk>/update", views_prompts_api.sc_update, name="api_sc_update"),
    path("api/subcategories/<int:pk>/delete", views_prompts_api.sc_delete, name="api_sc_delete"),
    path("api/prompt-categories/<int:category_id>/subcategories", views_prompts_api.category_subcategories_api, name="api_pc_subcategories"),
    path("api/subcategories/<int:subcategory_id>/prompts", views_prompts_api.subcategory_prompts_api, name="api_sc_prompts"),

    # ── Взаимодействия с задачей (лайки/комменты/сохранения для всех работ)
    path("job/<int:pk>/like", views.job_like_toggle, name="job_like"),
    path("job/<int:pk>/save", views.job_save_toggle, name="job_save"),
    path("job/<int:pk>/likers", views.job_likers, name="job_likers"),
    path("job/<int:pk>/comment", views.job_comment_add, name="job_comment"),
    path("job/comment/<int:pk>/reply", views.job_comment_reply, name="job_comment_reply"),
    path("job/comment/<int:pk>/like", views.job_comment_like_toggle, name="job_comment_like"),

    # ── Удаление (GET подтверждение / POST действие) — обязательно выше slug-маршрутов
    path("job/<int:pk>/delete", views.job_confirm_delete, name="job_confirm_delete"),
    path("job/<int:pk>/delete/confirm", views.job_delete, name="job_delete"),

    # ── Спец-роуты задачи — также выше общего slug
    path("job/<int:pk>/<slug:slug>/status", views.job_status, name="job_status"),
    path("job/<int:pk>/status", views.job_status_no_slug, name="job_status_no_slug"),
    path("job/<int:pk>/<slug:slug>/image", views.job_image, name="job_image"),

    # ── Новые URL для фото и видео по slug с категорией
    path("photo/<slug:category_slug>/<slug:slug>", views.photo_detail, name="photo_detail"),
    path("video/<slug:category_slug>/<slug:slug>", views.video_detail, name="video_detail"),

    # ── Детали задачи без слага → редирект на канонический
    path("job/<int:pk>", views.job_detail_no_slug, name="job_detail_no_slug"),

    # ── Мои работы
    path("my", views.my_jobs_all, name="my_jobs"),
    path("api/guest-balance", views_api.guest_balance, name="api_guest_balance"),

    # ── API для категорий промптов
    path("api/categories/<int:category_id>/prompts", views.category_prompts_api, name="category_prompts_api"),

    # ── Детали задачи (общий slug-роут).
    # Негативный lookahead защищает от конфликтов со спец-суффиксами (delete/status/image).
    re_path(
        r"^job/(?P<pk>\d+)/(?!(?:delete|status|image)/?$)(?P<slug>[-\w]+)$",
        views.job_detail,
        name="job_detail",
    ),

    # Legacy URL redirects
    path("new/", RedirectView.as_view(pattern_name="generate:new", permanent=True)),
    path("api/submit/", RedirectView.as_view(pattern_name="generate:api_submit", permanent=True)),
    path("api/status/<int:job_id>/", RedirectView.as_view(pattern_name="generate:api_status", permanent=True)),
    path("api/runware/webhook/", RedirectView.as_view(pattern_name="generate:runware_webhook", permanent=True)),
    path("api/video/models/", RedirectView.as_view(pattern_name="generate:api_video_models", permanent=True)),
    path("api/video/submit/", RedirectView.as_view(pattern_name="generate:api_video_submit", permanent=True)),
    path("api/video/status/<int:job_id>/", RedirectView.as_view(pattern_name="generate:api_video_status", permanent=True)),
    path("api/video/categories/<int:category_id>/prompts/", RedirectView.as_view(pattern_name="generate:api_video_category_prompts", permanent=True)),
    path("api/job/<int:pk>/persist/", RedirectView.as_view(pattern_name="generate:api_job_persist", permanent=True)),
    path("api/suggestions/create/", RedirectView.as_view(pattern_name="generate:api_suggestion_create", permanent=True)),
    path("api/suggestions/<int:pk>/update/", RedirectView.as_view(pattern_name="generate:api_suggestion_update", permanent=True)),
    path("api/suggestions/<int:pk>/delete/", RedirectView.as_view(pattern_name="generate:api_suggestion_delete", permanent=True)),
    path("api/suggestion-categories/create/", RedirectView.as_view(pattern_name="generate:api_cat_create", permanent=True)),
    path("api/suggestion-categories/<int:pk>/update/", RedirectView.as_view(pattern_name="generate:api_cat_update", permanent=True)),
    path("api/suggestion-categories/<int:pk>/delete/", RedirectView.as_view(pattern_name="generate:api_cat_delete", permanent=True)),
    path("api/prompt-categories/create/", RedirectView.as_view(pattern_name="generate:api_pc_create", permanent=True)),
    path("api/prompt-categories/<int:pk>/update/", RedirectView.as_view(pattern_name="generate:api_pc_update", permanent=True)),
    path("api/prompt-categories/<int:pk>/delete/", RedirectView.as_view(pattern_name="generate:api_pc_delete", permanent=True)),
    path("api/prompts/create/", RedirectView.as_view(pattern_name="generate:api_cp_create", permanent=True)),
    path("api/prompts/<int:pk>/update/", RedirectView.as_view(pattern_name="generate:api_cp_update", permanent=True)),
    path("api/prompts/<int:pk>/delete/", RedirectView.as_view(pattern_name="generate:api_cp_delete", permanent=True)),
    path("job/<int:pk>/delete/", RedirectView.as_view(pattern_name="generate:job_confirm_delete", permanent=True)),
    path("job/<int:pk>/delete/confirm/", RedirectView.as_view(pattern_name="generate:job_delete", permanent=True)),
    path("job/<int:pk>/<slug:slug>/status/", RedirectView.as_view(pattern_name="generate:job_status", permanent=True)),
    path("job/<int:pk>/status/", RedirectView.as_view(pattern_name="generate:job_status_no_slug", permanent=True)),
    path("job/<int:pk>/<slug:slug>/image/", RedirectView.as_view(pattern_name="generate:job_image", permanent=True)),
    path("job/<int:pk>/", RedirectView.as_view(pattern_name="generate:job_detail_no_slug", permanent=True)),
    path("my/", RedirectView.as_view(pattern_name="generate:my_jobs", permanent=True)),
    path("api/guest-balance/", RedirectView.as_view(pattern_name="generate:api_guest_balance", permanent=True)),
    path("api/categories/<int:category_id>/prompts/", RedirectView.as_view(pattern_name="generate:category_prompts_api", permanent=True)),
]
