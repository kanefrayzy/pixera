from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


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
    guest_jobs_limit = models.PositiveIntegerField(default=abuse_guest_jobs_limit)
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
            self.guest_jobs_limit = max(int(self.guest_jobs_limit), int(other.guest_jobs_limit))
            self.guest_jobs_used = max(int(self.guest_jobs_used), int(other.guest_jobs_used))
            self.save(update_fields=["guest_jobs_limit", "guest_jobs_used", "updated_at"])
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
            ident = AbuseIdentifier.objects.filter(kind=kind, value=AbuseIdentifier.normalize(kind, val)).select_related("cluster").first()
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
        FP   = "fp", "Fingerprint"
        GID  = "gid", "Cookie GID"
        IP   = "ip", "IP hash"
        UA   = "ua", "UA hash"
        USER = "user", "User ID"

    kind = models.CharField(max_length=8, choices=Kind.choices, db_index=True)
    value = models.CharField(max_length=128, db_index=True)
    cluster = models.ForeignKey(AbuseCluster, related_name="identifiers", on_delete=models.CASCADE)

    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Анти-абуз идентификатор"
        verbose_name_plural = "Анти-абуз идентификаторы"
        constraints = [
            models.UniqueConstraint(fields=["kind", "value"], name="uq_abuse_identifier_kind_value"),
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
    description = models.CharField("Описание", max_length=200, blank=True, default="")
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


# ====== Основная задача генерации ============================================

class GenerationJob(models.Model):
    """Задача генерации изображения."""
    class Status(models.TextChoices):
        PENDING = "PENDING", "В очереди"
        RUNNING = "RUNNING", "Обработка"
        DONE    = "DONE",    "Готово"
        FAILED  = "FAILED",  "Ошибка"
        PENDING_MODERATION = "PENDING_MODERATION", "Ожидает модерации"

    # --- принадлежность и гостевые идентификаторы ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="generation_jobs",
    )
    guest_session_key = models.CharField(max_length=64, blank=True, default="")
    guest_gid = models.CharField(max_length=64, blank=True, default="", db_index=True)
    guest_fp  = models.CharField(max_length=64, blank=True, default="", db_index=True)

    cluster = models.ForeignKey(
        "AbuseCluster",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="jobs",
    )

    # --- параметры генерации ---
    prompt = models.TextField()
    model_id = models.CharField(max_length=100, default=default_model_id)

    # --- статус и ошибки ---
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    error = models.TextField(blank=True, default="")

    # --- результат ---
    result_image = models.ImageField(upload_to="gen/%Y/%m/", null=True, blank=True)

    # --- публикация ---
    is_public = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)

    # --- таймстемпы ---
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    # --- биллинг/токены ---
    tokens_spent = models.PositiveIntegerField(default=0)

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


# ====== Бесплатный грант гостя ==============================================

class FreeGrant(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        db_index=True
    )

    # Идентификаторы гостя
    gid = models.CharField(max_length=64, blank=True, db_index=True, default="")
    fp = models.CharField(max_length=64, blank=True, db_index=True, default="")
    ua_hash = models.CharField(max_length=64, blank=True, db_index=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, db_index=True, default="")
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
                grant.fp = fp; changed = True
            if gid and not grant.gid:
                grant.gid = gid; changed = True
            if ua_hash and not grant.ua_hash:
                grant.ua_hash = ua_hash; changed = True
            if ip_hash and not grant.ip_hash:
                grant.ip_hash = ip_hash; changed = True
            if first_ip and not grant.first_ip:
                grant.first_ip = first_ip; changed = True
            if changed:
                grant.save(update_fields=["fp", "gid", "ua_hash", "ip_hash", "first_ip", "updated_at"])
            return grant

        # 2) Фолбэк: «приклеиваемся» к недавнему UA (например, 30 дней)
        if ua_hash:
            since = timezone.now() - timezone.timedelta(days=30)
            recent = cls.objects.filter(ua_hash=ua_hash, created_at__gte=since).order_by("created_at").first()
            if recent:
                changed = False
                if fp and not recent.fp:
                    recent.fp = fp; changed = True
                if gid and not recent.gid:
                    recent.gid = gid; changed = True
                if ip_hash and not recent.ip_hash:
                    recent.ip_hash = ip_hash; changed = True
                if first_ip and not recent.first_ip:
                    recent.first_ip = first_ip; changed = True
                if changed:
                    recent.save(update_fields=["fp", "gid", "ip_hash", "first_ip", "updated_at"])
                return recent

        # 3) Не нашли — создаём новый один раз для этой связки
        total = int(initial_tokens if initial_tokens is not None else guest_initial_tokens())
        return cls.objects.create(
            fp=fp, gid=gid, ua_hash=ua_hash, ip_hash=ip_hash, first_ip=first_ip, total=total, consumed=0
        )
