# gallery/models.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.text import slugify


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


class PublicPhoto(models.Model):
    """
    Единственная валидная модель публикации в галерее.
    ВАЖНО: denorm-поля likes_count / comments_count поддерживаем атомарно во вьюхах через F().
    """
    image = models.ImageField(upload_to="public/%Y/%m/")
    title = models.CharField(max_length=140, blank=True)
    caption = models.CharField(max_length=240, blank=True)
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
