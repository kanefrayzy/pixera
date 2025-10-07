# blog/models.py
from __future__ import annotations

from typing import Optional

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .utils import transliterate_slug


# ──────────────────────────────────────────────────────────────────────────────
# Tag
# ──────────────────────────────────────────────────────────────────────────────
class Tag(models.Model):
    name = models.CharField("Название", max_length=48, unique=True)
    # убираем allow_unicode=True, теперь используем только латинские символы
    slug = models.SlugField("Слаг", max_length=64, unique=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = transliterate_slug(self.name) or "tag"
            slug = base
            i = 2
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        return super().save(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Менеджер опубликованных постов
# ──────────────────────────────────────────────────────────────────────────────
class PostQuerySet(models.QuerySet):
    def published(self) -> "PostQuerySet":
        return self.filter(is_published=True, published_at__lte=timezone.now())


# ──────────────────────────────────────────────────────────────────────────────
# Post
# ──────────────────────────────────────────────────────────────────────────────
class Post(models.Model):
    title = models.CharField("Заголовок", max_length=180)
    # убираем allow_unicode=True, теперь используем только латинские символы
    slug = models.SlugField("Слаг", max_length=200, unique=True, blank=True)
    cover = models.ImageField("Обложка", upload_to="blog/covers/")
    excerpt = models.TextField("Краткое описание", max_length=300, blank=True)
    body = models.TextField("Текст статьи", blank=True)

    # теги
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="posts",
        verbose_name="Теги",
        help_text="Список тегов для фильтрации и SEO.",
    )

    # SEO
    meta_title = models.CharField(
        "Meta title", max_length=180, blank=True,
        help_text="Если пусто — берём обычный заголовок.",
    )
    meta_description = models.CharField(
        "Meta description", max_length=300, blank=True,
        help_text="Короткое SEO-описание для сниппета.",
    )
    og_title = models.CharField("OG title", max_length=180, blank=True)
    og_description = models.CharField("OG description", max_length=300, blank=True)
    og_image = models.ImageField(
        "OG image", upload_to="blog/og/", blank=True, null=True,
        help_text="Если пусто — используем обложку.",
    )

    # публикация
    is_published = models.BooleanField("Опубликовано", default=False, db_index=True)
    published_at = models.DateTimeField("Дата публикации", default=timezone.now, db_index=True)

    # системные
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Пост"
        verbose_name_plural = "Посты"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_published", "published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    # URL
    def get_absolute_url(self) -> str:
        return reverse("blog:detail", kwargs={"slug": self.slug})

    # slug-генерация
    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            # режем запас по длине (чуть меньше max_length, чтобы влезли суффиксы -2, -3, ...)
            base = transliterate_slug(self.title)[:190]
            slug = base
            i = 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # SEO/OG геттеры
    def seo_title(self) -> str:
        return self.meta_title or self.title

    def seo_description(self) -> str:
        return (self.meta_description or self.excerpt or "")[:300]

    def og_title_fallback(self) -> str:
        return self.og_title or self.seo_title()

    def og_description_fallback(self) -> str:
        return self.og_description or self.seo_description()

    def og_image_url(self) -> Optional[str]:
        img = self.og_image or self.cover
        return img.url if img else None
