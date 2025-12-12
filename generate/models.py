from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Iterable
import io
from PIL import Image

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# Import ReferenceImage model
from .models_reference import ReferenceImage


# ====== helpers / defaults ====================================================

def default_model_id() -> str:
    """ID модели генерации по умолчанию (RUNWARE_DEFAULT_MODEL)."""
    return getattr(settings, "RUNWARE_DEFAULT_MODEL", "runware:101@1")


def token_cost() -> int:
    """Стоимость одной обработки в токенах."""
    return int(getattr(settings, "TOKEN_COST_PER_GEN", 10) or 10)


def guest_initial_tokens() -> int:
    """Стартовая квота гостя в токенах."""
    return int(getattr(settings, "GUEST_INITIAL_TOKENS", 30) or 30)


def abuse_guest_jobs_limit() -> int:
    """Сколько бесплатных обработок можно сделать на кластер (по умолчанию 3)."""
    return int(getattr(settings, "ABUSE_MAX_GUEST_JOBS", 3) or 3)


log = logging.getLogger(__name__)


# =============================================================================
# АНТИ-АБУЗ: Кластер + Идентификаторы
# =============================================================================

class AbuseCluster(models.Model):
    """
    Кластер «одного пользователя» — объединяет разные идентификаторы:
    fp, gid, ip_hash, ua_hash, а при авторизации — user_id.

    Лимит на бесплатные задачи держим на уровне кластера (а не отдельной куки/сессии).
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # счётчик бесплатных «обработок» (в штуках, не токенах)
    guest_jobs_limit = models.PositiveIntegerField(
        default=abuse_guest_jobs_limit)
    guest_jobs_used = models.PositiveIntegerField(default=0)

    note = models.CharField(max_length=240, blank=True, default="")

    class Meta:
        verbose_name = "Анти-абуз кластер"
        verbose_name_plural = "Анти-абуз кластеры"

    def __str__(self) -> str:
        return f"Cluster#{self.pk} used={self.guest_jobs_used}/{self.guest_jobs_limit}"

    # ---- лимиты (в обработках) ----------------------------------------------
    @property
    def jobs_left(self) -> int:
        return max(0, int(self.guest_jobs_limit) - int(self.guest_jobs_used))

    def can_consume_jobs(self, amount: int = 1) -> bool:
        return self.jobs_left >= max(0, int(amount or 0))

    @transaction.atomic
    def consume_jobs(self, amount: int = 1) -> int:
        """Идемпотентно списать N «обработок». Возвращает фактически списанное."""
        amount = max(0, int(amount or 0))
        if amount == 0:
            return 0
        c = AbuseCluster.objects.select_for_update().get(pk=self.pk)
        left = max(0, int(c.guest_jobs_limit) - int(c.guest_jobs_used))
        spend = min(left, amount)
        if spend > 0:
            c.guest_jobs_used = int(c.guest_jobs_used) + spend
            c.save(update_fields=["guest_jobs_used", "updated_at"])
        return spend

    # ---- union/merge ---------------------------------------------------------
    @transaction.atomic
    def merge_from(self, others: Iterable["AbuseCluster"]) -> "AbuseCluster":
        """
        Слить в текущий кластер все из `others`.
        Лимит/использование берём максимумом, чтобы не «дарить» попытки при склейке.
        """
        for other in (o for o in others if o and o.pk and o.pk != self.pk):
            AbuseIdentifier.objects.filter(cluster=other).update(cluster=self)
            self.guest_jobs_limit = max(
                int(self.guest_jobs_limit), int(other.guest_jobs_limit))
            self.guest_jobs_used = max(
                int(self.guest_jobs_used), int(other.guest_jobs_used))
            self.save(update_fields=["guest_jobs_limit",
                      "guest_jobs_used", "updated_at"])
            other.delete()
        return self

    # ---- фабрика/резолвер ----------------------------------------------------
    @classmethod
    @transaction.atomic
    def ensure_for(
        cls,
        *,
        fp: str | None = None,
        gid: str | None = None,
        ip_hash: str | None = None,
        ua_hash: str | None = None,
        user_id: int | None = None,
        create_if_missing: bool = True,
    ) -> "AbuseCluster":
        """
        Находит/создаёт кластер, опираясь на любой из переданных идентификаторов.
        Если найдено несколько разных кластеров — аккуратно склеиваем их в один.
        Затем привязываем ВСЕ переданные идентификаторы к итоговому кластеру.
        """
        ids = []
        probe = [
            ("fp", AbuseIdentifier.Kind.FP, fp),
            ("gid", AbuseIdentifier.Kind.GID, gid),
            ("ip", AbuseIdentifier.Kind.IP, ip_hash),
            ("ua", AbuseIdentifier.Kind.UA, ua_hash),
            ("user", AbuseIdentifier.Kind.USER, str(user_id) if user_id else None),
        ]
        clusters: dict[int, AbuseCluster] = {}
        for _, kind, val in probe:
            if not val:
                continue
            ident = AbuseIdentifier.objects.filter(kind=kind, value=AbuseIdentifier.normalize(
                kind, val)).select_related("cluster").first()
            if ident:
                ids.append(ident)
                if ident.cluster_id:
                    clusters[ident.cluster_id] = ident.cluster

        if clusters:
            base = next(iter(clusters.values()))
            if len(clusters) > 1:
                others = [c for cid, c in clusters.items() if cid != base.pk]
                base.merge_from(others)
            cluster = base
        else:
            if not create_if_missing:
                raise cls.DoesNotExist("No cluster for given identifiers")
            cluster = cls.objects.create(
                guest_jobs_limit=abuse_guest_jobs_limit(),
                guest_jobs_used=0,
            )

        for _, kind, val in probe:
            if not val:
                continue
            AbuseIdentifier.attach(cluster=cluster, kind=kind, value=val)

        return cluster


class AbuseIdentifier(models.Model):
    """Уникальный идентификатор (kind + value), привязан к кластеру."""
    class Kind(models.TextChoices):
        FP = "fp", "Fingerprint"
        GID = "gid", "Cookie GID"
        IP = "ip", "IP hash"
        UA = "ua", "UA hash"
        USER = "user", "User ID"

    kind = models.CharField(max_length=8, choices=Kind.choices, db_index=True)
    value = models.CharField(max_length=128, db_index=True)
    cluster = models.ForeignKey(
        AbuseCluster, related_name="identifiers", on_delete=models.CASCADE)

    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Анти-абуз идентификатор"
        verbose_name_plural = "Анти-абуз идентификаторы"
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "value"], name="uq_abuse_identifier_kind_value"),
        ]
        indexes = [
            models.Index(fields=("kind", "value")),
            models.Index(fields=("cluster", "kind")),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.value[:10]}… → C{self.cluster_id}"

    @staticmethod
    def normalize(kind: str, value: str) -> str:
        return (value or "").strip().lower()

    @classmethod
    def attach(cls, *, cluster: AbuseCluster, kind: "AbuseIdentifier.Kind", value: str) -> "AbuseIdentifier":
        norm = cls.normalize(kind, value)
        try:
            ident = cls.objects.select_for_update().get(kind=kind, value=norm)
            if ident.cluster_id != cluster.pk:
                cluster.merge_from([ident.cluster])
                ident.cluster = cluster
                ident.save(update_fields=["cluster", "last_seen"])
            else:
                ident.save(update_fields=["last_seen"])
            return ident
        except cls.DoesNotExist:
            return cls.objects.create(kind=kind, value=norm, cluster=cluster)


# ====== Подсказки для промптов (с категориями) ===============================

class SuggestionCategory(models.Model):
    """Категория для подсказок (видна в UI над полем промпта)."""
    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Слаг", max_length=80, unique=True, db_index=True)
    description = models.CharField(
        "Описание", max_length=200, blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория подсказок"
        verbose_name_plural = "Категории подсказок"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:80]
        super().save(*args, **kwargs)


class Suggestion(models.Model):
    """Подсказка/пресет для формы генерации (можно группировать по категориям)."""
    category = models.ForeignKey(
        SuggestionCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="suggestions",
        verbose_name="Категория",
    )
    title = models.CharField("Заголовок", max_length=80, unique=True)
    text = models.TextField("Текст подсказки")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Подсказка"
        verbose_name_plural = "Подсказки"

    def __str__(self) -> str:
        return self.title


# ====== Новые категории промптов с изображениями =============================

class PromptCategory(models.Model):
    """Категория промптов с изображением для интерактивного выбора."""
    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField("Слаг", max_length=100, unique=True, db_index=True)
    description = models.TextField("Описание", blank=True, default="")
    image = models.ImageField(
        "Изображение категории", upload_to="prompt_categories/", blank=True, null=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория промптов"
        verbose_name_plural = "Категории промптов"
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:100]
        super().save(*args, **kwargs)

    @property
    def active_prompts_count(self) -> int:
        """Количество активных промптов в категории."""
        return self.prompts.filter(is_active=True).count()


class PromptSubcategory(models.Model):
    """Подкатегория внутри категории промптов (второй уровень навигации)."""
    category = models.ForeignKey(
        "PromptCategory",
        on_delete=models.CASCADE,
        related_name="subcategories",
        verbose_name="Категория"
    )
    name = models.CharField("Название", max_length=120)
    slug = models.SlugField("Слаг", max_length=140, db_index=True)
    description = models.TextField("Описание", blank=True, default="")
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Подкатегория промптов"
        verbose_name_plural = "Подкатегории промптов"
        constraints = [
            models.UniqueConstraint(fields=["category", "slug"], name="uq_prompt_subcat_category_slug"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:140]
        super().save(*args, **kwargs)


class CategoryPrompt(models.Model):
    """Промпт внутри категории."""
    category = models.ForeignKey(
        PromptCategory,
        on_delete=models.CASCADE,
        related_name="prompts",
        verbose_name="Категория"
    )
    subcategory = models.ForeignKey(
        "PromptSubcategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prompts",
        verbose_name="Подкатегория"
    )
    title = models.CharField("Заголовок", max_length=150)
    prompt_text = models.TextField("Текст промпта")
    prompt_en = models.TextField(
        "Английский промпт",
        blank=True,
        default="",
        help_text="Профессиональный английский промпт для генерации"
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активен", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Промпт категории"
        verbose_name_plural = "Промпты категорий"
        indexes = [
            models.Index(fields=["category", "is_active", "order"]),
            models.Index(fields=["subcategory", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name}: {self.title}"

    def get_prompt_for_generation(self) -> str:
        """Возвращает английский промпт если есть, иначе русский."""
        return self.prompt_en.strip() if self.prompt_en.strip() else self.prompt_text


# ====== Витрина: примеры изображений (админ добавляет) =======================

class ShowcaseCategory(models.Model):
    """Категории для примеров (для SEO-блока с образцами)."""
    name = models.CharField("Название", max_length=80, unique=True)
    slug = models.SlugField("Слаг", max_length=80, unique=True, db_index=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория примеров"
        verbose_name_plural = "Категории примеров"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:80]
        super().save(*args, **kwargs)


class ShowcaseImage(models.Model):
    """
    Пример изображения с промптом для SEO/обучающего блока.
    Управляется только админом в админке/модерации.
    """
    image = models.ImageField(upload_to="showcase/%Y/%m/")
    title = models.CharField(max_length=140)
    prompt = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        ShowcaseCategory,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="images",
    )
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_showcase_images",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("order", "-created_at")
        verbose_name = "Пример изображения"
        verbose_name_plural = "Примеры изображений"

    def __str__(self) -> str:
        return self.title or f"Showcase #{self.pk}"

    def get_all_images(self):
        """Возвращает список всех изображений (основное + дополнительные)"""
        images = []
        if self.image:
            images.append(self.image.url)

        # Получаем дополнительные изображения с полными объектами
        additional_objs = self.additional_images.filter(
            is_active=True).order_by('order')
        for add_img in additional_objs:
            if add_img.image:
                images.append(add_img.image.url)

        return images

    def _make_thumbnail(self, image_field, width: int = 480, quality: int = 70) -> Optional[str]:
        if not image_field:
            return None
        try:
            name = Path(image_field.name)
            thumb_dir = f"showcase/thumbs/{width}/"
            thumb_name = thumb_dir + f"{name.stem}_{width}.jpg"
            # If exists, return cached url
            if default_storage.exists(thumb_name):
                return default_storage.url(thumb_name)
            # Ensure source exists
            if not default_storage.exists(image_field.name):
                return getattr(image_field, "url", None)
            # Open, resize and save to storage
            with default_storage.open(image_field.name, "rb") as f:
                im = Image.open(f)
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                w, h = im.size
                if w == 0 or h == 0:
                    return getattr(image_field, "url", None)
                new_h = max(1, int(h * (width / float(w))))
                im = im.resize((int(width), int(new_h)), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=int(
                    quality), optimize=True, progressive=True)
                buf.seek(0)
                default_storage.save(thumb_name, ContentFile(buf.read()))
            return default_storage.url(thumb_name)
        except Exception:
            # Fallback to original
            return getattr(image_field, "url", None)

    def get_all_images_with_thumbs(self, width: int = 480, quality: int = 70):
        """
        Возвращает список объектов с миниатюрой и полным изображением:
        [{ 'thumb': <url>, 'full': <url> }, ...]
        """
        out = []
        if self.image:
            out.append({
                "thumb": self._make_thumbnail(self.image, width=width, quality=quality),
                "full": getattr(self.image, "url", None)
            })
        additional_objs = self.additional_images.filter(
            is_active=True).order_by('order')
        for add_img in additional_objs:
            if add_img.image:
                out.append({
                    "thumb": self._make_thumbnail(add_img.image, width=width, quality=quality),
                    "full": getattr(add_img.image, "url", None)
                })
        return out


class ShowcaseAdditionalImage(models.Model):
    """Дополнительные изображения для showcase примера (для слайдера)"""
    showcase = models.ForeignKey(
        ShowcaseImage,
        on_delete=models.CASCADE,
        related_name="additional_images",
        verbose_name="Пример"
    )
    image = models.ImageField(
        upload_to="showcase/%Y/%m/additional/", verbose_name="Изображение")
    order = models.PositiveIntegerField(
        default=0, db_index=True, verbose_name="Порядок")
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "created_at")
        verbose_name = "Дополнительное изображение"
        verbose_name_plural = "Дополнительные изображения"

    def __str__(self) -> str:
        return f"Доп. изображение #{self.order} для {self.showcase.title}"


# ====== Модели для генерации видео ============================================

class VideoModel(models.Model):
    """Модель для генерации видео через Runware API."""

    class Category(models.TextChoices):
        T2V = "t2v", "Text-to-Video"
        I2V = "i2v", "Image-to-Video"
        ANIME = "anime", "Anime"

    class ReferenceType(models.TextChoices):
        """Типы входных данных для видео-моделей."""
        FRAME_IMAGES = "frameImages", "Frame Images"
        REFERENCE_IMAGES = "referenceImages", "Reference Images"
        AUDIO_INPUTS = "audioInputs", "Audio Inputs"
        CONTROL_NET = "controlNet", "ControlNet"

    name = models.CharField("Название", max_length=100)
    model_id = models.CharField(
        "ID модели", max_length=50, unique=True, db_index=True)
    category = models.CharField(
        "Категория", max_length=20, choices=Category.choices, default=Category.T2V)
    description = models.TextField("Описание", blank=True, default="")
    token_cost = models.PositiveIntegerField("Стоимость в токенах", default=18)
    max_duration = models.PositiveIntegerField(
        "Макс. длительность (сек)", default=8)
    max_resolution = models.CharField(
        "Макс. разрешение", max_length=20, default="1920x1080")

    # Поддерживаемые типы референсов (JSON: список строк из ReferenceType)
    supported_references = models.JSONField(
        "Поддерживаемые референсы",
        default=list,
        blank=True,
        help_text="Типы входных данных, которые поддерживает модель (frameImages, referenceImages, audioInputs, controlNet)"
    )

    is_active = models.BooleanField("Активна", default=True, db_index=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Модель видео"
        verbose_name_plural = "Модели видео"
        indexes = [
            models.Index(fields=["is_active", "category", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.model_id}) - {self.token_cost} TOK"


class VideoPromptCategory(models.Model):
    """Категория промптов для видео (аналог PromptCategory для изображений)."""

    class Mode(models.TextChoices):
        I2V = "i2v", "Image-to-Video"
        T2V = "t2v", "Text-to-Video"

    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField("Слаг", max_length=100, unique=True, db_index=True)
    description = models.TextField("Описание", blank=True, default="")
    image = models.ImageField(
        "Изображение категории", upload_to="video_prompt_categories/", blank=True, null=True)
    mode = models.CharField(
        "Режим", max_length=10, choices=Mode.choices, default=Mode.T2V, db_index=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Категория промптов видео"
        verbose_name_plural = "Категории промптов видео"
        indexes = [
            models.Index(fields=["is_active", "mode", "order"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:100]
        super().save(*args, **kwargs)

    @property
    def active_prompts_count(self) -> int:
        """Количество активных промптов в категории."""
        return self.video_prompts.filter(is_active=True).count()


class VideoPromptSubcategory(models.Model):
    """Подкатегория внутри категории видеопромптов (второй уровень)."""
    category = models.ForeignKey(
        "VideoPromptCategory",
        on_delete=models.CASCADE,
        related_name="subcategories",
        verbose_name="Категория"
    )
    name = models.CharField("Название", max_length=120)
    slug = models.SlugField("Слаг", max_length=140, db_index=True)
    description = models.TextField("Описание", blank=True, default="")
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Подкатегория видеопромптов"
        verbose_name_plural = "Подкатегории видеопромптов"
        constraints = [
            models.UniqueConstraint(fields=["category", "slug"], name="uq_video_prompt_subcat_category_slug"),
        ]
        indexes = [
            models.Index(fields=["category", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name or "")[:140]
        super().save(*args, **kwargs)


class VideoPrompt(models.Model):
    """Промпт для генерации видео внутри категории."""
    category = models.ForeignKey(
        VideoPromptCategory,
        on_delete=models.CASCADE,
        related_name="video_prompts",
        verbose_name="Категория"
    )
    subcategory = models.ForeignKey(
        "VideoPromptSubcategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="video_prompts",
        verbose_name="Подкатегория"
    )
    title = models.CharField("Заголовок", max_length=150)
    prompt_text = models.TextField("Текст промпта")
    prompt_en = models.TextField(
        "Английский промпт",
        blank=True,
        default="",
        help_text="Профессиональный английский промпт для генерации видео"
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активен", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Промпт видео"
        verbose_name_plural = "Промпты видео"
        indexes = [
            models.Index(fields=["category", "is_active", "order"]),
            models.Index(fields=["subcategory", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name}: {self.title}"

    def get_prompt_for_generation(self) -> str:
        """Возвращает английский промпт если есть, иначе русский."""
        return self.prompt_en.strip() if self.prompt_en.strip() else self.prompt_text


class ShowcaseVideo(models.Model):
    """Примеры видео для витрины (аналог ShowcaseImage)."""

    class Mode(models.TextChoices):
        I2V = "i2v", "Image-to-Video"
        T2V = "t2v", "Text-to-Video"

    video_url = models.URLField("URL видео", max_length=500)
    thumbnail = models.ImageField(
        "Превью", upload_to="video_thumbnails/%Y/%m/", blank=True)
    title = models.CharField("Название", max_length=140)
    prompt = models.TextField("Промпт", blank=True, default="")
    mode = models.CharField(
        "Режим", max_length=10, choices=Mode.choices, default=Mode.T2V, db_index=True)
    category = models.ForeignKey(
        ShowcaseCategory,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="videos",
        verbose_name="Категория"
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активно", default=True, db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_showcase_videos",
        verbose_name="Загрузил"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("order", "-created_at")
        verbose_name = "Пример видео"
        verbose_name_plural = "Примеры видео"
        indexes = [
            models.Index(fields=["is_active", "mode", "order"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Video #{self.pk}"


# ====== Основная задача генерации ============================================

class GenerationJob(models.Model):
    """Задача генерации изображения."""
    class Status(models.TextChoices):
        PENDING = "PENDING", "В очереди"
        RUNNING = "RUNNING", "Обработка"
        DONE = "DONE",    "Готово"
        FAILED = "FAILED",  "Ошибка"
        PENDING_MODERATION = "PENDING_MODERATION", "Ожидает модерации"

    # --- принадлежность и гостевые идентификаторы ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="generation_jobs",
    )
    guest_session_key = models.CharField(max_length=64, blank=True, default="")
    guest_gid = models.CharField(
        max_length=64, blank=True, default="", db_index=True)
    guest_fp = models.CharField(
        max_length=64, blank=True, default="", db_index=True)

    cluster = models.ForeignKey(
        "AbuseCluster",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="jobs",
    )

    # --- тип генерации ---
    generation_type = models.CharField(
        max_length=10,
        choices=[("image", "Изображение"), ("video", "Видео")],
        default="image",
        db_index=True
    )

    # --- параметры генерации ---
    prompt = models.TextField()
    original_prompt = models.TextField(
        blank=True, default="", help_text="Оригинальный промпт до перевода")
    model_id = models.CharField(max_length=100, default=default_model_id)

    # --- параметры видео (если generation_type == 'video') ---
    video_model = models.ForeignKey(
        "VideoModel",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="jobs",
        verbose_name="Модель видео"
    )
    video_duration = models.PositiveIntegerField(
        "Длительность видео (сек)", null=True, blank=True)
    video_aspect_ratio = models.CharField(
        "Соотношение сторон", max_length=10, blank=True, default="")  # 16:9, 9:16, 1:1
    video_resolution = models.CharField(
        "Разрешение", max_length=20, blank=True, default="")
    video_camera_movement = models.CharField(
        "Движение камеры", max_length=50, blank=True, default="")
    video_seed = models.CharField(
        "Seed", max_length=50, blank=True, default="")

    # --- для Image-to-Video ---
    video_source_image = models.ImageField(
        "Исходное изображение", upload_to="video_sources/%Y/%m/", null=True, blank=True)
    video_motion_strength = models.PositiveIntegerField(
        "Сила движения", null=True, blank=True, default=45)

    # --- статус и ошибки ---
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    error = models.TextField(blank=True, default="")

    # --- результат ---
    result_image = models.ImageField(
        upload_to="gen/%Y/%m/", null=True, blank=True)
    result_video_url = models.URLField(
        "URL видео", max_length=500, blank=True, default="")
    video_cached_until = models.DateTimeField(
        "Видео кешировано до", null=True, blank=True)

    # --- публикация ---
    is_public = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)

    # --- таймстемпы ---
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    # --- биллинг/токены ---
    tokens_spent = models.PositiveIntegerField(default=0)

    # --- сохранение в "Мои генерации" (новая логика) ---
    # Новые задачи по умолчанию не попадают в "Мои генерации", пока пользователь не сохранит их вручную.
    # Для существующих записей выставим True в дата-миграции.
    persisted = models.BooleanField(default=False, db_index=True)

    # --- async Runware ---
    provider_task_uuid = models.CharField(
        max_length=64, blank=True, default="", db_index=True
    )
    provider_status = models.CharField(max_length=32, blank=True, default="")
    provider_payload = models.JSONField(null=True, blank=True)
    last_polled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Задача генерации"
        verbose_name_plural = "Задачи генерации"
        indexes = [
            models.Index(fields=("user", "created_at")),
            models.Index(fields=("is_public", "created_at")),
            models.Index(fields=("guest_session_key", "created_at")),
            models.Index(fields=("guest_gid", "created_at")),
            models.Index(fields=("guest_fp", "created_at")),
            models.Index(fields=("status", "created_at")),
            models.Index(fields=("provider_task_uuid",)),
            models.Index(fields=("cluster", "created_at")),
        ]

    def __str__(self) -> str:
        return f"Job #{self.pk or '∅'} — {self.get_status_display()}"

    @property
    def is_done(self) -> bool:
        return self.status == self.Status.DONE

    @property
    def is_running(self) -> bool:
        return self.status == self.Status.RUNNING

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_failed(self) -> bool:
        return self.status == self.Status.FAILED

    @property
    def has_result_file(self) -> bool:
        f = getattr(self, "result_image", None)
        name = getattr(f, "name", "") or ""
        if not name:
            return False
        try:
            return default_storage.exists(name)
        except Exception:
            return False

    @property
    def result_url(self) -> Optional[str]:
        try:
            if self.result_image and self.result_image.url:
                return self.result_image.url
        except Exception:
            pass
        return None

    @property
    def result_basename(self) -> Optional[str]:
        name = getattr(self.result_image, "name", "") or ""
        return Path(name).name if name else None

    @property
    def can_share(self) -> bool:
        return self.is_done and (self.has_result_file or self.result_url)

    @property
    def diamonds_spent(self) -> int:
        c = token_cost() or 1
        return (int(self.tokens_spent) // c) if self.tokens_spent else 0

    def get_share_url(self) -> str:
        return reverse("gallery:share_from_job", args=[self.pk])

    def mark_public(self, trending: bool = False) -> None:
        self.is_public = True
        self.is_trending = bool(trending)
        self.save(update_fields=["is_public", "is_trending"])

    def get_reference_images(self):
        """Получить все референсные изображения для этой задачи."""
        return self.reference_images.all().order_by('order')

    def get_reference_images_urls(self):
        """Получить список URL всех референсных изображений."""
        return [ref.image.url for ref in self.get_reference_images() if ref.image]

    def has_reference_images(self) -> bool:
        """Проверить, есть ли у задачи референсные изображения."""
        return self.reference_images.exists()

    def reference_images_count(self) -> int:
        """Количество референсных изображений."""
        return self.reference_images.count()

    @classmethod
    @transaction.atomic
    def claim_for_user(
        cls,
        *,
        user,
        session_key: str | None = None,
        guest_gid: str | None = None,
        guest_fp: str | None = None,
    ) -> int:
        """
        Присвоить все гостевые задачи (без user_id) пользователю, если они связаны
        с текущими guest-идентификаторами (session_key/gid/fp).
        """
        if not user:
            return 0

        q = Q(user__isnull=True)
        any_id = False
        if session_key:
            q &= Q(guest_session_key=session_key) | Q(guest_session_key="")
            any_id = True
        if guest_gid:
            q |= Q(user__isnull=True, guest_gid=guest_gid)
            any_id = True
        if guest_fp:
            q |= Q(user__isnull=True, guest_fp=guest_fp)
            any_id = True

        if not any_id:
            return 0

        updated = (
            cls.objects
            .filter(q)
            .update(user=user, guest_session_key="", guest_gid="", guest_fp="")
        )
        return int(updated)


# ====== Отслеживание устройств и безопасность ================================

class DeviceFingerprint(models.Model):
    """
    УЛУЧШЕННОЕ отслеживание устройства с гибридной защитой.
    Уровень 1: FP (клиентский отпечаток: canvas+WebGL+browser API)
    Уровень 2: GID (стойкий cookie)
    Уровень 3: UA hash (отпечаток User-Agent)
    Уровень 4: IP hash (защита от VPN, не для идентификации)
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 4 уровня защиты
    fp = models.CharField(max_length=64, db_index=True, help_text='Клиентский отпечаток браузера (canvas+WebGL)')
    server_fp = models.CharField(max_length=64, db_index=True, blank=True, default='', help_text='Серверный отпечаток (fallback)')
    gid = models.CharField(max_length=64, db_index=True, help_text='Стойкий cookie идентификатор')
    ip_hash = models.CharField(max_length=64, db_index=True, help_text='Хеш IP адреса')
    ua_hash = models.CharField(max_length=64, db_index=True, help_text='Хеш User-Agent')

    # Дополнительные данные
    first_ip = models.GenericIPAddressField(null=True, blank=True, help_text='Первый IP адрес')
    session_keys = models.JSONField(default=list, help_text='История session keys')

    # Флаги безопасности
    is_vpn_detected = models.BooleanField(default=False, db_index=True, help_text='Обнаружен VPN')
    is_incognito_detected = models.BooleanField(default=False, db_index=True, help_text='Обнаружен инкогнито')
    is_blocked = models.BooleanField(default=False, db_index=True, help_text='Заблокирован за попытки обхода')

    # Счётчики попыток обхода
    bypass_attempts = models.PositiveIntegerField(default=0, help_text='Попытки обхода системы')
    last_bypass_attempt = models.DateTimeField(null=True, blank=True)

    # Связь с FreeGrant (один к одному)
    free_grant = models.OneToOneField(
        'FreeGrant',
        on_delete=models.CASCADE,
        related_name='device_fingerprint',
        null=True,
        blank=True,
        help_text='Связанный грант'
    )

    class Meta:
        verbose_name = 'Отпечаток устройства'
        verbose_name_plural = 'Отпечатки устройств'
        indexes = [
            models.Index(fields=['fp', 'is_blocked']),
            models.Index(fields=['server_fp', 'is_blocked']),
            models.Index(fields=['gid', 'is_blocked']),
            models.Index(fields=['gid', 'ua_hash']),
            models.Index(fields=['ip_hash', 'is_blocked']),
            models.Index(fields=['ua_hash', 'is_blocked']),
            models.Index(fields=['is_blocked', 'created_at']),
        ]

    def __str__(self) -> str:
        return f"Device#{self.pk} fp={self.fp[:8]}... blocked={self.is_blocked}"

    @classmethod
    @transaction.atomic
    def get_or_create_device(
        cls,
        *,
        fp: str,
        gid: str,
        ip_hash: str,
        ua_hash: str,
        server_fp: str = "",
        first_ip: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> tuple["DeviceFingerprint", bool]:
        """
        УЛУЧШЕННАЯ ЛОГИКА: приоритет клиентскому fingerprint.
        Возвращает (device, created).

        СТРАТЕГИЯ ПОИСКА:
        1. Ищем по клиентскому FP (canvas+WebGL - самый надёжный)
        2. Если не найдено - ищем по GID + UA_HASH (игнорируем IP!)
        3. Если найдено по GID+UA но с другим FP = обновляем FP (VPN/Tor)
        4. Если не найдено - проверяем server_fp как fallback
        5. Иначе создаём новое устройство
        
        IP НЕ используется для идентификации (только для VPN-детекта)!
        """
        fp = (fp or "").strip()
        gid = (gid or "").strip()
        ip_hash = (ip_hash or "").strip()
        ua_hash = (ua_hash or "").strip()
        server_fp = (server_fp or "").strip()

        if not fp and not server_fp:
            raise ValueError("Either client FP or server FP is required")

        # Уровень 1: Поиск по клиентскому FP (приоритет)
        if fp:
            device = cls.objects.filter(fp=fp, is_blocked=False).first()
            if device:
                # Найдено по клиентскому FP - обновляем метаданные
                updated = False
                
                if gid and device.gid != gid:
                    device.gid = gid
                    updated = True
                
                if server_fp and device.server_fp != server_fp:
                    device.server_fp = server_fp
                    updated = True
                    
                if ip_hash and device.ip_hash != ip_hash:
                    # IP изменился - возможно VPN/Tor (это нормально!)
                    if device.ip_hash:
                        device.is_vpn_detected = True
                    device.ip_hash = ip_hash
                    updated = True
                    
                if ua_hash and device.ua_hash != ua_hash:
                    device.ua_hash = ua_hash
                    updated = True
                    
                if first_ip and not device.first_ip:
                    device.first_ip = first_ip
                    updated = True
                    
                if session_key:
                    keys = device.session_keys or []
                    if session_key not in keys:
                        keys.append(session_key)
                        device.session_keys = keys[-10:]
                        updated = True

                if updated:
                    device.save()

                return device, False

        # Уровень 2: Поиск по GID + UA_HASH (игнорируем IP!)
        # Это позволяет находить устройство даже при смене IP через VPN/Tor
        if gid and ua_hash:
            similar = cls.objects.filter(
                gid=gid,
                ua_hash=ua_hash,
                is_blocked=False
            ).first()

            if similar:
                # Найдено устройство с тем же GID+UA но другим клиентским FP
                # Это может быть:
                # 1) Нормальная смена IP через VPN/Tor
                # 2) Попытка обхода через инкогнито
                
                # Проверяем: если клиентский FP сильно отличается - подозрительно
                if fp and similar.fp != fp:
                    # Клиент прислал новый FP - это может быть инкогнито
                    similar.bypass_attempts += 1
                    similar.last_bypass_attempt = timezone.now()
                    similar.is_incognito_detected = True
                    
                    # НЕ блокируем сразу, даем шанс (может быть смена браузера)
                    # Блокируем только после многих попыток
                    if similar.bypass_attempts >= 5:
                        similar.is_blocked = True
                        similar.save()
                        
                        TokenGrantAttempt.objects.create(
                            fp=fp,
                            gid=gid,
                            ip_hash=ip_hash,
                            ua_hash=ua_hash,
                            session_key=session_key or '',
                            ip_address=first_ip,
                            was_granted=False,
                            was_blocked=True,
                            block_reason='Множественные попытки обхода обнаружены',
                            device=similar
                        )
                        return similar, False
                    
                    # Обновляем FP (разрешаем использование)
                    similar.fp = fp
                
                # Обновляем остальные данные
                similar.server_fp = server_fp
                if ip_hash and similar.ip_hash != ip_hash:
                    similar.is_vpn_detected = True
                    similar.ip_hash = ip_hash
                if first_ip and not similar.first_ip:
                    similar.first_ip = first_ip
                if session_key:
                    keys = similar.session_keys or []
                    if session_key not in keys:
                        keys.append(session_key)
                        similar.session_keys = keys[-10:]
                        
                similar.save()
                return similar, False

        # Уровень 3: Fallback на серверный FP (если клиентского нет)
        if server_fp and not fp:
            device = cls.objects.filter(server_fp=server_fp, is_blocked=False).first()
            if device:
                # Обновляем метаданные
                updated = False
                if gid and device.gid != gid:
                    device.gid = gid
                    updated = True
                if ip_hash and device.ip_hash != ip_hash:
                    device.is_vpn_detected = True
                    device.ip_hash = ip_hash
                    updated = True
                if ua_hash and device.ua_hash != ua_hash:
                    device.ua_hash = ua_hash
                    updated = True
                if updated:
                    device.save()
                return device, False

        # Создаём новое устройство
        device = cls.objects.create(
            fp=fp or server_fp,  # Используем клиентский или fallback на серверный
            server_fp=server_fp,
            gid=gid,
            ip_hash=ip_hash,
            ua_hash=ua_hash,
            first_ip=first_ip,
            session_keys=[session_key] if session_key else []
        )

        return device, True

    def can_get_tokens(self) -> tuple[bool, str]:
        """
        Проверка: может ли устройство получить токены.
        Возвращает (can_get, reason).
        """
        if self.is_blocked:
            return False, "Устройство заблокировано за попытки обхода системы"

        if self.free_grant and self.free_grant.left <= 0:
            return False, "Токены уже использованы"

        return True, ""

    def record_bypass_attempt(self, reason: str = "") -> None:
        """Записать попытку обхода системы."""
        self.bypass_attempts += 1
        self.last_bypass_attempt = timezone.now()

        if self.bypass_attempts >= 3:
            self.is_blocked = True

        self.save(update_fields=['bypass_attempts', 'last_bypass_attempt', 'is_blocked', 'updated_at'])


class TokenGrantAttempt(models.Model):
    """Лог попыток получения токенов для анализа и безопасности."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Идентификаторы попытки
    fp = models.CharField(max_length=64, db_index=True)
    gid = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, db_index=True)
    ua_hash = models.CharField(max_length=64, db_index=True)
    session_key = models.CharField(max_length=64, blank=True, default='')

    # IP адрес
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Результат попытки
    was_granted = models.BooleanField(default=False, help_text='Были ли выданы токены')
    was_blocked = models.BooleanField(default=False, help_text='Была ли попытка заблокирована')
    block_reason = models.CharField(max_length=200, blank=True, default='', help_text='Причина блокировки')

    # Связь с устройством
    device = models.ForeignKey(
        'DeviceFingerprint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grant_attempts'
    )

    class Meta:
        verbose_name = 'Попытка получения токенов'
        verbose_name_plural = 'Попытки получения токенов'
        indexes = [
            models.Index(fields=['fp', 'created_at']),
            models.Index(fields=['gid', 'created_at']),
            models.Index(fields=['ip_hash', 'created_at']),
            models.Index(fields=['was_blocked', 'created_at']),
        ]

    def __str__(self) -> str:
        status = "GRANTED" if self.was_granted else ("BLOCKED" if self.was_blocked else "DENIED")
        return f"Attempt#{self.pk} {status} fp={self.fp[:8]}..."


# ====== Бесплатный грант гостя ==============================================

class FreeGrant(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        db_index=True
    )

    # Идентификаторы гостя
    gid = models.CharField(max_length=64, blank=True,
                           db_index=True, default="")
    fp = models.CharField(max_length=64, blank=True, db_index=True, default="")
    ua_hash = models.CharField(
        max_length=64, blank=True, db_index=True, default="")
    ip_hash = models.CharField(
        max_length=64, blank=True, db_index=True, default="")
    first_ip = models.GenericIPAddressField(null=True, blank=True)

    # Лимит и расход (в токенах)
    total = models.PositiveIntegerField(default=guest_initial_tokens)
    consumed = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["gid"]),
            models.Index(fields=["fp"]),
            models.Index(fields=["ip_hash"]),
            models.Index(fields=["ua_hash"]),
        ]

    def __str__(self) -> str:
        return f"FreeGrant#{self.pk} left={self.left}"

    @property
    def left(self) -> int:
        return max(int(self.total) - int(self.consumed), 0)

    @property
    def is_bound_to_user(self) -> bool:
        """Проверяет, привязан ли грант к пользователю."""
        return self.user_id is not None

    def spend(self, amount: int) -> int:
        """Списать amount, вернуть фактически списанное."""
        amount = max(int(amount), 0)
        if amount == 0:
            return 0

        # Защита от попытки списания с уже привязанного гранта
        if self.is_bound_to_user:
            log.warning(f"Attempt to spend from bound grant {self.pk}")
            return 0

        can = self.left
        take = min(can, amount)
        if take <= 0:
            return 0
        self.consumed = int(self.consumed) + take
        self.save(update_fields=["consumed", "updated_at"])
        return take

    def bind_to_user(self, user, transfer_left: bool = True) -> None:
        """Привязать грант к пользователю, опционально переложив остаток в кошелёк."""
        if not user:
            return

        # Защита от повторного переноса токенов
        if self.user_id == user.id:
            # Грант уже привязан к этому пользователю
            return

        from dashboard.models import Wallet  # локальный импорт, чтобы не ловить циклы
        with transaction.atomic():
            # Повторная проверка под блокировкой
            grant = FreeGrant.objects.select_for_update().get(pk=self.pk)
            if grant.user_id == user.id:
                return  # Уже привязан

            if transfer_left:
                left = grant.left
                if left > 0:
                    wallet, _ = Wallet.objects.get_or_create(user=user)
                    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                    wallet.balance = int(wallet.balance or 0) + left
                    wallet.save(update_fields=["balance"])
                    grant.consumed = int(grant.total)  # остаток списали

            grant.user = user
            grant.save(update_fields=["user", "consumed", "updated_at"])

            # Обновляем текущий объект
            self.user = user
            self.consumed = grant.consumed

    @classmethod
    def ensure_for(
        cls,
        *,
        fp: str,
        gid: str,
        session_key: str,   # для совместимости — не используется в поиске
        ua_hash: str,
        ip_hash: str,
        first_ip: Optional[str] = None,
        initial_tokens: Optional[int] = None,
    ) -> "FreeGrant":
        """
        Находим/создаём один грант на устройство/пользователя, склеивая по fp|gid|ip_hash.
        ВАЖНО: добавлен «фолбэк по UA» на недавний период — чтобы инкогнито через ngrok
        НЕ получал новый пакет (если это тот же браузер).
        """
        fp = (fp or "").strip()
        gid = (gid or "").strip()
        ua_hash = (ua_hash or "").strip()
        ip_hash = (ip_hash or "").strip()

        # 1) Ищем существующий по жёстким ключам
        q = Q()
        if fp:
            q |= Q(fp=fp)
        if gid:
            q |= Q(gid=gid)
        if ip_hash:
            q |= Q(ip_hash=ip_hash)

        grant = cls.objects.filter(q).order_by("created_at").first()
        if grant:
            changed = False
            if fp and not grant.fp:
                grant.fp = fp
                changed = True
            if gid and not grant.gid:
                grant.gid = gid
                changed = True
            if ua_hash and not grant.ua_hash:
                grant.ua_hash = ua_hash
                changed = True
            if ip_hash and not grant.ip_hash:
                grant.ip_hash = ip_hash
                changed = True
            if first_ip and not grant.first_ip:
                grant.first_ip = first_ip
                changed = True
            if changed:
                grant.save(update_fields=[
                           "fp", "gid", "ua_hash", "ip_hash", "first_ip", "updated_at"])
            return grant

        # 2) Фолбэк: «приклеиваемся» к недавнему UA (например, 30 дней)
        if ua_hash:
            since = timezone.now() - timezone.timedelta(days=30)
            recent = cls.objects.filter(
                ua_hash=ua_hash, created_at__gte=since).order_by("created_at").first()
            if recent:
                changed = False
                if fp and not recent.fp:
                    recent.fp = fp
                    changed = True
                if gid and not recent.gid:
                    recent.gid = gid
                    changed = True
                if ip_hash and not recent.ip_hash:
                    recent.ip_hash = ip_hash
                    changed = True
                if first_ip and not recent.first_ip:
                    recent.first_ip = first_ip
                    changed = True
                if changed:
                    recent.save(update_fields=[
                                "fp", "gid", "ip_hash", "first_ip", "updated_at"])
                return recent

        # 3) Не нашли — создаём новый один раз для этой связки
        total = int(
            initial_tokens if initial_tokens is not None else guest_initial_tokens())
        return cls.objects.create(
            fp=fp, gid=gid, ua_hash=ua_hash, ip_hash=ip_hash, first_ip=first_ip, total=total, consumed=0
        )


# ====== Import VideoModelConfiguration =======================================
# Импортируем новую модель для управления видео моделями
from .models_video import VideoModelConfiguration
from .models_image import ImageModelConfiguration

__all__ = [
    'AbuseCluster',
    'AbuseIdentifier',
    'SuggestionCategory',
    'Suggestion',
    'PromptCategory',
    'PromptSubcategory',
    'CategoryPrompt',
    'ShowcaseCategory',
    'ShowcaseImage',
    'ShowcaseAdditionalImage',
    'VideoModel',
    'VideoPromptCategory',
    'VideoPromptSubcategory',
    'VideoPrompt',
    'ShowcaseVideo',
    'GenerationJob',
    'DeviceFingerprint',
    'TokenGrantAttempt',
    'FreeGrant',
    'ReferenceImage',
    'VideoModelConfiguration',
    'ImageModelConfiguration',
]
