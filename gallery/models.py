# gallery/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.text import slugify
from .models_slider_video import VideoSliderExample
from uuid import uuid4

# Robust slugify to ASCII using python-slugify when available (fallback to Django's slugify)
try:
    from slugify import slugify as _slugify_ascii  # python-slugify
    def make_slug(text: str) -> str:
        # Force ASCII transliteration so any language becomes an English slug
        return _slugify_ascii(text or "", allow_unicode=False)
except Exception:
    def make_slug(text: str) -> str:
        # Fallback: Django's slugify (may not transliterate all locales)
        from django.utils.text import slugify as _dj_slugify
        return _dj_slugify(text or "")


class Category(models.Model):
    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Слаг", max_length=80, unique=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name or "")
        super().save(*args, **kwargs)


class VideoCategory(models.Model):
    """Категории для видео (отдельные от фото)."""
    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Слаг", max_length=80, unique=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория видео"
        verbose_name_plural = "Категории видео"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name or "")
        super().save(*args, **kwargs)


class PublicPhoto(models.Model):
    """
    Единственная валидная модель публикации в галерее.
    ВАЖНО: denorm-поля likes_count / comments_count поддерживаем атомарно во вьюхах через F().
    """
    image = models.ImageField(upload_to="public/%Y/%m/")
    title = models.CharField(max_length=140, blank=True)
    caption = models.CharField(max_length=240, blank=True)
    slug = models.SlugField("Слаг", max_length=180, unique=True, null=True, blank=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_public_photos",
    )

    # связь с задачей генерации (нужна для «добавлено в галерею» на /my-jobs/)
    source_job = models.ForeignKey(
        "generate.GenerationJob",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="public_entries",
        db_index=True,
    )

    category = models.ForeignKey(
        "Category",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="photos",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # счётчики (денормализованные)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    likes_count = models.PositiveIntegerField(default=0, db_index=True)
    comments_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("order", "-created_at")
        verbose_name = "Публичное фото"
        verbose_name_plural = "Публичные фото"

    def __str__(self) -> str:
        return self.title or f"PublicPhoto #{self.pk}"

    def get_absolute_url(self) -> str:
        from django.urls import reverse

        # SEO-friendly URL с категорией: /gallery/<category-slug>/photo/<photo-slug>
        if getattr(self, "slug", None) and self.category and self.category.slug:
            return reverse("gallery:category_photo_detail", args=[self.category.slug, self.slug])
        elif getattr(self, "slug", None):
            # Fallback: без категории
            return reverse("gallery:slug_detail", args=[self.slug])
        return reverse("gallery:photo_detail", args=[self.pk])

    def save(self, *args, **kwargs) -> None:
        # Сначала сохраняем чтобы получить pk, если его еще нет
        is_new = self.pk is None
        if is_new:
            super().save(*args, **kwargs)
        
        # Автогенерация slug из title при отсутствии (транслитерация в ASCII)
        if not getattr(self, "slug", None):
            # make_slug гарантирует английский slug из любого языка
            base = make_slug(self.title)[:120] or "photo"
            # Добавляем ID в конец slug для уникальности и совместимости с generate
            self.slug = f"{base}-{self.pk}"
        
        if not is_new:
            super().save(*args, **kwargs)


class PhotoLike(models.Model):
    """
    Лайк публичного фото.
    Уникально по (photo,user) или (photo,session_key).
    Для гостя храним session_key (пустая строка — «нет»).
    """
    photo = models.ForeignKey(PublicPhoto, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
        related_name="photo_likes",
    )
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк фото"
        verbose_name_plural = "Лайки фото"
        constraints = [
            # один лайк на (фото, пользователь)
            UniqueConstraint(
                fields=["photo", "user"],
                condition=Q(user__isnull=False),
                name="uq_photo_like_user",
            ),
            # один лайк на (фото, гостевая сессия) — если session_key не пустой
            UniqueConstraint(
                fields=["photo", "session_key"],
                condition=~Q(session_key=""),
                name="uq_photo_like_session",
            ),
        ]

    def __str__(self) -> str:
        who = f"u{self.user_id}" if self.user_id else f"sess:{self.session_key or '-'}"
        return f"❤ {who} -> photo {self.photo_id}"


class PhotoComment(models.Model):
    """
    Комментарий к фото (поддержка вложенности через parent).
    Денорм-поле likes_count поддерживаем атомарно во вьюхах.
    """
    photo = models.ForeignKey(PublicPhoto, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_visible = models.BooleanField(default=True, db_index=True)

    # древовидные ответы
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )

    # счётчик лайков на комментарии (денорм)
    likes_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

    def __str__(self) -> str:
        return f"Comment #{self.pk} on {self.photo_id}"


class CommentLike(models.Model):
    """Лайк комментария. Уникально по (comment,user) или (comment,session_key)."""
    comment = models.ForeignKey(PhotoComment, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк комментария"
        verbose_name_plural = "Лайки комментариев"
        constraints = [
            UniqueConstraint(
                fields=["comment", "user"],
                condition=Q(user__isnull=False),
                name="uq_comment_like_user",
            ),
            UniqueConstraint(
                fields=["comment", "session_key"],
                condition=~Q(session_key=""),
                name="uq_comment_like_session",
            ),
        ]

    def __str__(self) -> str:
        who = f"u{self.user_id}" if self.user_id else f"sess:{self.session_key or '-'}"
        return f"Like c{self.comment_id} by {who}"


class Image(models.Model):
    """
    Личная галерея пользователя (изображения и видео).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    prompt = models.TextField(blank=True)
    image_url = models.URLField(max_length=500)  # URL изображения или видео
    is_video = models.BooleanField(default=False, db_index=True)  # Флаг видео
    is_public = models.BooleanField(default=False, db_index=True)
    is_nsfw = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Связь с задачей генерации
    generation_job = models.ForeignKey(
        "generate.GenerationJob",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="gallery_entries",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Изображение галереи"
        verbose_name_plural = "Изображения галереи"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_video"]),
        ]

    def __str__(self) -> str:
        media_type = "Видео" if self.is_video else "Изображение"
        return f"{media_type} #{self.pk} пользователя {self.user.username}"


class PublicVideo(models.Model):
    """
    Публичное видео в галерее (аналог PublicPhoto).
    """
    video_url = models.URLField("URL видео", max_length=500)
    thumbnail = models.ImageField("Превью", upload_to="public_videos/%Y/%m/", null=True, blank=True)
    title = models.CharField("Название", max_length=140, blank=True)
    caption = models.CharField("Описание", max_length=240, blank=True)
    slug = models.SlugField("Слаг", max_length=180, unique=True, null=True, blank=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField("Опубликовано", default=True, db_index=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_public_videos",
        verbose_name="Загрузил"
    )

    # Связь с задачей генерации
    source_job = models.ForeignKey(
        "generate.GenerationJob",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="public_video_entries",
        db_index=True,
        verbose_name="Задача генерации"
    )

    category = models.ForeignKey(
        "VideoCategory",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="videos",
        verbose_name="Категория"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Счётчики (денормализованные)
    view_count = models.PositiveIntegerField("Просмотры", default=0, db_index=True)
    likes_count = models.PositiveIntegerField("Лайки", default=0, db_index=True)
    comments_count = models.PositiveIntegerField("Комментарии", default=0, db_index=True)

    class Meta:
        ordering = ("order", "-created_at")
        verbose_name = "Публичное видео"
        verbose_name_plural = "Публичные видео"

    def __str__(self) -> str:
        return self.title or f"PublicVideo #{self.pk}"

    def get_absolute_url(self) -> str:
        from django.urls import reverse

        # SEO-friendly URL с категорией: /gallery/<category-slug>/video/<video-slug>
        if getattr(self, "slug", None) and self.category and self.category.slug:
            return reverse("gallery:category_video_detail", args=[self.category.slug, self.slug])
        elif getattr(self, "slug", None):
            # Fallback: без категории
            return reverse("gallery:slug_detail", args=[self.slug])
        return reverse("gallery:video_detail_by_pk", args=[self.pk])

    def save(self, *args, **kwargs) -> None:
        # Сначала сохраняем чтобы получить pk, если его еще нет
        is_new = self.pk is None
        if is_new:
            super().save(*args, **kwargs)
        
        # Автогенерация слага из заголовка; обеспечение уникальности
        if not getattr(self, "slug", None):
            base = slugify(self.title or "")[:120] or "video"
            # Добавляем ID в конец slug для уникальности и совместимости с generate
            self.slug = f"{base}-{self.pk}"
        
        if not is_new:
            super().save(*args, **kwargs)


class VideoLike(models.Model):
    """
    Лайк публичного видео (аналог PhotoLike).
    """
    video = models.ForeignKey(PublicVideo, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
        related_name="video_likes",
    )
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк видео"
        verbose_name_plural = "Лайки видео"
        constraints = [
            UniqueConstraint(
                fields=["video", "user"],
                condition=Q(user__isnull=False),
                name="uq_video_like_user",
            ),
            UniqueConstraint(
                fields=["video", "session_key"],
                condition=~Q(session_key=""),
                name="uq_video_like_session",
            ),
        ]

    def __str__(self) -> str:
        who = f"u{self.user_id}" if self.user_id else f"sess:{self.session_key or '-'}"
        return f"❤ {who} -> video {self.video_id}"


class PhotoSave(models.Model):
    """
    Сохранения (закладки) публичных фото пользователями.
    """
    photo = models.ForeignKey(PublicPhoto, on_delete=models.CASCADE, related_name="saves")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="photo_saves")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Сохранение фото"
        verbose_name_plural = "Сохранения фото"
        constraints = [
            UniqueConstraint(fields=["photo", "user"], name="uq_photo_save_user"),
        ]

    def __str__(self) -> str:
        return f"🔖 u{self.user_id} -> photo {self.photo_id}"


class VideoSave(models.Model):
    """
    Сохранения (закладки) публичных видео пользователями.
    """
    video = models.ForeignKey(PublicVideo, on_delete=models.CASCADE, related_name="saves")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_saves")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Сохранение видео"
        verbose_name_plural = "Сохранения видео"
        constraints = [
            UniqueConstraint(fields=["video", "user"], name="uq_video_save_user"),
        ]

    def __str__(self) -> str:
        return f"🔖 u{self.user_id} -> video {self.video_id}"


class VideoComment(models.Model):
    """
    Комментарий к видео (аналог PhotoComment).
    """
    video = models.ForeignKey(PublicVideo, related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField("Текст")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_visible = models.BooleanField("Видимый", default=True, db_index=True)

    # Древовидные ответы
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE,
        verbose_name="Родительский комментарий"
    )

    # Счётчик лайков
    likes_count = models.PositiveIntegerField("Лайки", default=0, db_index=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Комментарий к видео"
        verbose_name_plural = "Комментарии к видео"

    def __str__(self) -> str:
        return f"Comment #{self.pk} on video {self.video_id}"


class VideoCommentLike(models.Model):
    """
    Лайк комментария к видео (аналог CommentLike).
    """
    comment = models.ForeignKey(VideoComment, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк комментария к видео"
        verbose_name_plural = "Лайки комментариев к видео"
        constraints = [
            UniqueConstraint(
                fields=["comment", "user"],
                condition=Q(user__isnull=False),
                name="uq_video_comment_like_user",
            ),
            UniqueConstraint(
                fields=["comment", "session_key"],
                condition=~Q(session_key=""),
                name="uq_video_comment_like_session",
            ),
        ]

    def __str__(self) -> str:
        who = f"u{self.user_id}" if self.user_id else f"sess:{self.session_key or '-'}"
        return f"Like vc{self.comment_id} by {who}"


class Like(models.Model):
    """
    (Если используешь) Лайки для GenerationJob — отдельно от лайков галереи.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="job_likes", null=True, blank=True,
    )
    job = models.ForeignKey(
        "generate.GenerationJob", on_delete=models.CASCADE,
        related_name="likes", null=True, blank=True, db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк задачи"
        verbose_name_plural = "Лайки задач"
        constraints = [
            UniqueConstraint(
                fields=["user", "job"],
                condition=Q(job__isnull=False) & Q(user__isnull=False),
                name="uq_job_like_user",
            ),
        ]

    def __str__(self) -> str:
        return f"JobLike#{self.pk} by {self.user_id} job={self.job_id}"


class JobSave(models.Model):
    """
    Закладки (сохранения) для любых задач GenerationJob — работают и для неопубликованных.
    Уникально по (user, job).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="job_saves",
    )
    job = models.ForeignKey(
        "generate.GenerationJob", on_delete=models.CASCADE,
        related_name="saves", db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Сохранение задачи"
        verbose_name_plural = "Сохранения задач"
        constraints = [
            UniqueConstraint(fields=["user", "job"], name="uq_job_save_user"),
        ]

    def __str__(self) -> str:
        return f"🔖 u{self.user_id} -> job {self.job_id}"

class JobHide(models.Model):
    """
    Скрытие задачи из профиля владельца.
    Уникально по (user, job). Публикации в галерее не влияют — они видимы всегда.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_hides",
    )
    job = models.ForeignKey(
        "generate.GenerationJob",
        on_delete=models.CASCADE,
        related_name="hides",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Скрытие задачи"
        verbose_name_plural = "Скрытия задач"
        constraints = [
            UniqueConstraint(fields=["user", "job"], name="uq_job_hide_user"),
        ]

    def __str__(self) -> str:
        return f"🙈 u{self.user_id} hides job {self.job_id}"


class JobComment(models.Model):
    """
    Комментарий к задаче GenerationJob (поддержка вложенных ответов).
    Денорм-поле likes_count поддерживается атомарно во вьюхах.
    """
    job = models.ForeignKey("generate.GenerationJob", related_name="comments", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_visible = models.BooleanField(default=True, db_index=True)

    # древовидные ответы
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )

    # счётчик лайков на комментарии (денорм)
    likes_count = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "Комментарий к задаче"
        verbose_name_plural = "Комментарии к задачам"

    def __str__(self) -> str:
        return f"JobComment #{self.pk} on job {self.job_id}"


class JobCommentLike(models.Model):
    """Лайк комментария к задаче. Уникально по (comment,user) или (comment,session_key)."""
    comment = models.ForeignKey(JobComment, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Лайк комментария к задаче"
        verbose_name_plural = "Лайки комментариев к задачам"
        constraints = [
            UniqueConstraint(
                fields=["comment", "user"],
                condition=Q(user__isnull=False),
                name="uq_job_comment_like_user",
            ),
            UniqueConstraint(
                fields=["comment", "session_key"],
                condition=~Q(session_key=""),
                name="uq_job_comment_like_session",
            ),
        ]

    def __str__(self) -> str:
        who = f"u{self.user_id}" if self.user_id else f"sess:{self.session_key or '-'}"
        return f"Like jc{self.comment_id} by {who}"
