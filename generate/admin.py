# generate/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import (
    GenerationJob,
    Suggestion,
    SuggestionCategory,
    FreeGrant,
    DeviceFingerprint,
    TokenGrantAttempt,
    ShowcaseCategory,
    ShowcaseImage,
    ShowcaseVideo,
    PromptCategory,
    CategoryPrompt,
    VideoModel,
    VideoPromptCategory,
    VideoPrompt,
)
from .models_reference import ReferenceImage
from .models_video import VideoModelConfiguration
from .models_aspect_ratio import AspectRatioQualityConfig, AspectRatioPreset
from .forms_video_model import VideoModelConfigurationForm

# ── Вспомогательные экшены ──────────────────────────────────────
@admin.action(description="Отметить как активные")
def mark_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Сделать неактивными")
def mark_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

# ── Подсказки ────────────────────────────────────────────────────
class SuggestionInline(admin.StackedInline):
    """
    Редактирование подсказок прямо внутри категории.
    """
    model = Suggestion
    extra = 0
    fields = ("title", "text", "is_active", "order")
    show_change_link = True

@admin.register(SuggestionCategory)
class SuggestionCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order", "suggestions_count")
    list_editable = ("is_active", "order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [SuggestionInline]
    actions = (mark_active, mark_inactive)

    @admin.display(description="Подсказок", ordering="id")
    def suggestions_count(self, obj):
        return obj.suggestions.count() if obj.pk else 0

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active", "order", "short_text")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "category")
    search_fields = ("title", "text")
    ordering = ("category__name", "order", "title")
    actions = (mark_active, mark_inactive)
    autocomplete_fields = ("category",)

    @admin.display(description="Текст")
    def short_text(self, obj):
        t = (obj.text or "").strip()
        return (t[:80] + "…") if len(t) > 80 else t

# ── Витрина (по желанию) ────────────────────────────────────────
class ShowcaseAdditionalImageInline(admin.TabularInline):
    """Дополнительные изображения для слайдера"""
    from .models import ShowcaseAdditionalImage
    model = ShowcaseAdditionalImage
    extra = 2
    fields = ("image", "order", "is_active")
    verbose_name = "Дополнительное изображение"
    verbose_name_plural = "Дополнительные изображения для слайдера"

class ShowcaseImageInline(admin.TabularInline):
    model = ShowcaseImage
    extra = 0
    fields = ("title", "image", "prompt", "is_active", "order")
    show_change_link = True

@admin.register(ShowcaseCategory)
class ShowcaseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [ShowcaseImageInline]

@admin.register(ShowcaseImage)
class ShowcaseImageAdmin(admin.ModelAdmin):
    list_display = ("thumb", "title", "category", "short_prompt", "images_count", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("title", "prompt")
    ordering = ("order", "-created_at")
    autocomplete_fields = ("category", "uploaded_by")
    readonly_fields = ("created_at", "preview_image")
    inlines = [ShowcaseAdditionalImageInline]

    fieldsets = (
        ("Основная информация", {
            "fields": ("title", "category", "is_active", "order")
        }),
        ("Изображение", {
            "fields": ("image", "preview_image"),
            "description": "Загрузите изображение для примера"
        }),
        ("Промпт", {
            "fields": ("prompt",),
            "description": "Введите промпт, который использовался для генерации этого изображения"
        }),
        ("Дополнительно", {
            "fields": ("uploaded_by", "created_at"),
            "classes": ("collapse",)
        }),
    )

    actions = (mark_active, mark_inactive)

    @admin.display(description="Превью")
    def thumb(self, obj):
        if getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="height:50px;width:50px;object-fit:cover;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)">',
                obj.image.url
            )
        return "—"

    @admin.display(description="Большое превью")
    def preview_image(self, obj):
        if getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="max-width:400px;max-height:400px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">',
                obj.image.url
            )
        return "Изображение не загружено"

    @admin.display(description="Промпт")
    def short_prompt(self, obj):
        p = (obj.prompt or "").strip()
        if not p:
            return format_html('<span style="color:#999;font-style:italic">Не указан</span>')
        return (p[:60] + "…") if len(p) > 60 else p

    @admin.display(description="Изображений")
    def images_count(self, obj):
        if not obj.pk:
            return "—"
        count = 1 + obj.additional_images.filter(is_active=True).count()
        if count > 1:
            return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count)
        return count

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)

# ── Референсные изображения ──────────────────────────────────────
class ReferenceImageInline(admin.TabularInline):
    """Inline для референсных изображений в GenerationJob"""
    model = ReferenceImage
    extra = 1
    max_num = 5
    fields = ("image", "order", "influence_weight", "preview")
    readonly_fields = ("preview", "uploaded_at")
    verbose_name = "Референсное изображение"
    verbose_name_plural = "Референсные изображения (до 5 шт.)"

    @admin.display(description="Превью")
    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px;width:60px;object-fit:cover;border-radius:8px">',
                obj.image.url
            )
        return "—"


@admin.register(ReferenceImage)
class ReferenceImageAdmin(admin.ModelAdmin):
    list_display = ("thumb", "job_link", "order", "influence_weight", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("job__id", "job__prompt")
    ordering = ("-uploaded_at",)
    readonly_fields = ("uploaded_at", "preview_image")

    fieldsets = (
        ("Основная информация", {
            "fields": ("job", "order", "influence_weight")
        }),
        ("Изображение", {
            "fields": ("image", "preview_image"),
        }),
        ("Дополнительно", {
            "fields": ("uploaded_at",),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Превью")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:50px;width:50px;object-fit:cover;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)">',
                obj.image.url
            )
        return "—"

    @admin.display(description="Большое превью")
    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:400px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">',
                obj.image.url
            )
        return "Изображение не загружено"

    @admin.display(description="Задача")
    def job_link(self, obj):
        if obj.job:
            return format_html(
                '<a href="/admin/generate/generationjob/{}/change/">Job #{}</a>',
                obj.job.id, obj.job.id
            )
        return "—"


# ── Остальные модели (как было) ─────────────────────────────────
@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "ref_count", "is_public", "is_trending", "created_at")
    list_filter = ("status", "is_public", "is_trending", "generation_type")
    search_fields = ("prompt", "user__username", "user__email")
    readonly_fields = ("created_at",)
    inlines = [ReferenceImageInline]

    @admin.display(description="Референсов")
    def ref_count(self, obj):
        if not obj.pk:
            return "—"
        count = obj.reference_images_count()
        if count > 0:
            return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count)
        return "0"

@admin.register(FreeGrant)
class FreeGrantAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "gid", "fp", "total", "consumed", "left", "first_ip", "has_device", "created_at")
    search_fields = ("gid", "fp", "user__username", "user__email", "first_ip")
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("user",)

    @admin.display(description="Устройство", boolean=True)
    def has_device(self, obj):
        return hasattr(obj, 'device_fingerprint') and obj.device_fingerprint is not None


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(admin.ModelAdmin):
    list_display = ("id", "fp_short", "gid_short", "is_blocked", "is_vpn_detected", "is_incognito_detected",
                    "bypass_attempts", "grant_left", "created_at")
    list_filter = ("is_blocked", "is_vpn_detected", "is_incognito_detected", "created_at")
    search_fields = ("fp", "gid", "ip_hash", "ua_hash", "first_ip")
    readonly_fields = ("created_at", "updated_at", "fp", "gid", "ip_hash", "ua_hash", "first_ip",
                       "session_keys", "last_bypass_attempt")
    list_editable = ("is_blocked",)

    fieldsets = (
        ("Идентификаторы (4-этапная защита)", {
            "fields": ("fp", "gid", "ip_hash", "ua_hash", "first_ip", "session_keys")
        }),
        ("Безопасность", {
            "fields": ("is_blocked", "is_vpn_detected", "is_incognito_detected",
                       "bypass_attempts", "last_bypass_attempt")
        }),
        ("Грант", {
            "fields": ("free_grant",)
        }),
        ("Дополнительно", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="FP")
    def fp_short(self, obj):
        return obj.fp[:12] + "..." if len(obj.fp) > 12 else obj.fp

    @admin.display(description="GID")
    def gid_short(self, obj):
        return obj.gid[:12] + "..." if len(obj.gid) > 12 else obj.gid

    @admin.display(description="Токенов осталось")
    def grant_left(self, obj):
        if obj.free_grant:
            left = obj.free_grant.left
            if left > 0:
                return format_html('<span style="color:#10b981;font-weight:600">{}</span>', left)
            return format_html('<span style="color:#ef4444">0</span>')
        return "—"

    actions = ["block_devices", "unblock_devices"]

    @admin.action(description="Заблокировать выбранные устройства")
    def block_devices(self, request, queryset):
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f"Заблокировано устройств: {updated}")

    @admin.action(description="Разблокировать выбранные устройства")
    def unblock_devices(self, request, queryset):
        updated = queryset.update(is_blocked=False, bypass_attempts=0)
        self.message_user(request, f"Разблокировано устройств: {updated}")


@admin.register(TokenGrantAttempt)
class TokenGrantAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "fp_short", "gid_short", "was_granted", "was_blocked", "block_reason_short",
                    "ip_address", "created_at")
    list_filter = ("was_granted", "was_blocked", "created_at")
    search_fields = ("fp", "gid", "ip_hash", "ua_hash", "ip_address", "block_reason")
    readonly_fields = ("created_at", "fp", "gid", "ip_hash", "ua_hash", "session_key", "ip_address",
                       "was_granted", "was_blocked", "block_reason", "device")
    date_hierarchy = "created_at"

    fieldsets = (
        ("Идентификаторы", {
            "fields": ("fp", "gid", "ip_hash", "ua_hash", "session_key", "ip_address")
        }),
        ("Результат", {
            "fields": ("was_granted", "was_blocked", "block_reason")
        }),
        ("Связи", {
            "fields": ("device",)
        }),
        ("Дополнительно", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="FP")
    def fp_short(self, obj):
        return obj.fp[:12] + "..." if len(obj.fp) > 12 else obj.fp

    @admin.display(description="GID")
    def gid_short(self, obj):
        return obj.gid[:12] + "..." if len(obj.gid) > 12 else obj.gid

    @admin.display(description="Причина блокировки")
    def block_reason_short(self, obj):
        if not obj.block_reason:
            return "—"
        reason = obj.block_reason[:50]
        if len(obj.block_reason) > 50:
            reason += "..."
        if obj.was_blocked:
            return format_html('<span style="color:#ef4444">{}</span>', reason)
        return reason

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ── Категории промптов с изображениями ──────────────────────────
class CategoryPromptInline(admin.TabularInline):
    model = CategoryPrompt
    extra = 3
    fields = ("title", "prompt_text", "is_active", "order")


@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "slug", "prompts_count", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [CategoryPromptInline]
    actions = (mark_active, mark_inactive)
    readonly_fields = ("created_at", "updated_at", "preview_image")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "slug", "description", "is_active", "order")
        }),
        ("Изображение категории", {
            "fields": ("image", "preview_image"),
        }),
        ("Дополнительно", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Превью")
    def thumb(self, obj):
        if getattr(obj, "image", None):
            try:
                return format_html(
                    '<img src="{}" style="height:60px;width:80px;object-fit:cover;border-radius:8px">',
                    obj.image.url
                )
            except:
                pass
        return format_html('<div style="height:60px;width:80px;background:#f3f4f6;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:11px">Нет</div>')

    @admin.display(description="Большое превью")
    def preview_image(self, obj):
        if getattr(obj, "image", None):
            try:
                return format_html('<img src="{}" style="max-width:600px;border-radius:12px">', obj.image.url)
            except:
                pass
        return "Изображение не загружено"

    @admin.display(description="Промптов")
    def prompts_count(self, obj):
        if not obj.pk:
            return "—"
        count = obj.active_prompts_count
        return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count) if count > 0 else "0"


@admin.register(CategoryPrompt)
class CategoryPromptAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "short_prompt", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "category")
    search_fields = ("title", "prompt_text", "category__name")
    ordering = ("category__order", "order", "title")
    actions = (mark_active, mark_inactive)
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at",)

    @admin.display(description="Промпт")
    def short_prompt(self, obj):
        p = (obj.prompt_text or "").strip()
        return (p[:60] + "…") if len(p) > 60 else p


# ── Модели видео ─────────────────────────────────────────────────
class VideoModelAdminForm(forms.ModelForm):
    """Форма для админки VideoModel с чекбоксами для типов референсов."""

    # Создаем поля с чекбоксами для каждого типа референса
    reference_frameImages = forms.BooleanField(
        label="Frame Images (массив изображений для I2V)",
        required=False,
        help_text="Модель поддерживает frameImages"
    )
    reference_referenceImages = forms.BooleanField(
        label="Reference Images (например, Wan2.5-Preview)",
        required=False,
        help_text="Модель поддерживает referenceImages"
    )
    reference_audioInputs = forms.BooleanField(
        label="Audio Inputs (аудио для V2V)",
        required=False,
        help_text="Модель поддерживает audioInputs"
    )
    reference_controlNet = forms.BooleanField(
        label="ControlNet (управление структурой)",
        required=False,
        help_text="Модель поддерживает controlNet"
    )

    class Meta:
        model = VideoModel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Заполняем чекбоксы из JSON-поля supported_references
        if self.instance and self.instance.pk:
            supported = self.instance.supported_references or []
            self.fields['reference_frameImages'].initial = 'frameImages' in supported
            self.fields['reference_referenceImages'].initial = 'referenceImages' in supported
            self.fields['reference_audioInputs'].initial = 'audioInputs' in supported
            self.fields['reference_controlNet'].initial = 'controlNet' in supported

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Собираем список поддерживаемых референсов из чекбоксов
        supported = []
        if self.cleaned_data.get('reference_frameImages'):
            supported.append('frameImages')
        if self.cleaned_data.get('reference_referenceImages'):
            supported.append('referenceImages')
        if self.cleaned_data.get('reference_audioInputs'):
            supported.append('audioInputs')
        if self.cleaned_data.get('reference_controlNet'):
            supported.append('controlNet')

        instance.supported_references = supported

        if commit:
            instance.save()
        return instance


@admin.register(VideoModel)
class VideoModelAdmin(admin.ModelAdmin):
    form = VideoModelAdminForm
    list_display = ("name", "model_id", "category", "token_cost", "max_duration", "is_active", "order", "display_references")
    list_editable = ("is_active", "order", "token_cost")
    list_filter = ("is_active", "category")
    search_fields = ("name", "model_id", "description")
    ordering = ("category", "order", "name")
    actions = (mark_active, mark_inactive)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "model_id", "category", "description")
        }),
        ("Параметры", {
            "fields": ("token_cost", "max_duration", "max_resolution")
        }),
        ("Поддерживаемые типы входных данных", {
            "fields": (
                "reference_frameImages",
                "reference_referenceImages",
                "reference_audioInputs",
                "reference_controlNet"
            ),
            "description": "Укажите, какие типы входных данных поддерживает модель"
        }),
        ("Настройки", {
            "fields": ("is_active", "order")
        }),
        ("Дополнительно", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Поддерживаемые референсы")
    def display_references(self, obj):
        """Отображение поддерживаемых референсов в списке."""
        if not obj.supported_references:
            return format_html('<span style="color: #999;">Не указано</span>')

        ref_labels = {
            'frameImages': 'FI',
            'referenceImages': 'RI',
            'audioInputs': 'AI',
            'controlNet': 'CN'
        }

        badges = []
        for ref_type in obj.supported_references:
            label = ref_labels.get(ref_type, ref_type[:2].upper())
            badges.append(f'<span style="background: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px; margin-right: 4px; font-size: 11px;">{label}</span>')

        return format_html(''.join(badges))

    @admin.display(description="Стоимость")
    def token_cost_display(self, obj):
        return format_html('<span style="color:#10b981;font-weight:600">{} TOK</span>', obj.token_cost)


@admin.register(ShowcaseVideo)
class ShowcaseVideoAdmin(admin.ModelAdmin):
    list_display = ("thumb", "title", "category", "short_prompt", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("title", "prompt", "video_url")
    ordering = ("order", "-created_at")
    autocomplete_fields = ("category", "uploaded_by")
    readonly_fields = ("created_at", "preview_thumbnail")

    fieldsets = (
        ("Основная информация", {
            "fields": ("title", "category", "is_active", "order")
        }),
        ("Видео", {
            "fields": ("video_url", "thumbnail", "preview_thumbnail"),
            "description": "URL видео и превью"
        }),
        ("Промпт", {
            "fields": ("prompt",),
            "description": "Промпт, использованный для генерации"
        }),
        ("Дополнительно", {
            "fields": ("uploaded_by", "created_at"),
            "classes": ("collapse",)
        }),
    )

    actions = (mark_active, mark_inactive)

    @admin.display(description="Превью")
    def thumb(self, obj):
        if getattr(obj, "thumbnail", None):
            return format_html(
                '<img src="{}" style="height:50px;width:80px;object-fit:cover;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1)">',
                obj.thumbnail.url
            )
        return "—"

    @admin.display(description="Большое превью")
    def preview_thumbnail(self, obj):
        if getattr(obj, "thumbnail", None):
            return format_html(
                '<img src="{}" style="max-width:400px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">',
                obj.thumbnail.url
            )
        return "Превью не загружено"

    @admin.display(description="Промпт")
    def short_prompt(self, obj):
        p = (obj.prompt or "").strip()
        if not p:
            return format_html('<span style="color:#999;font-style:italic">Не указан</span>')
        return (p[:60] + "…") if len(p) > 60 else p

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


# ── Категории промптов для видео ────────────────────────────────
class VideoPromptInline(admin.TabularInline):
    model = VideoPrompt
    extra = 3
    fields = ("title", "prompt_text", "is_active", "order")


@admin.register(VideoPromptCategory)
class VideoPromptCategoryAdmin(admin.ModelAdmin):
    list_display = ("thumb", "name", "slug", "prompts_count", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")
    inlines = [VideoPromptInline]
    actions = (mark_active, mark_inactive)
    readonly_fields = ("created_at", "updated_at", "preview_image")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "slug", "description", "is_active", "order")
        }),
        ("Изображение категории", {
            "fields": ("image", "preview_image"),
        }),
        ("Дополнительно", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Превью")
    def thumb(self, obj):
        if getattr(obj, "image", None):
            try:
                return format_html(
                    '<img src="{}" style="height:60px;width:80px;object-fit:cover;border-radius:8px">',
                    obj.image.url
                )
            except:
                pass
        return format_html('<div style="height:60px;width:80px;background:#f3f4f6;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:11px">Нет</div>')

    @admin.display(description="Большое превью")
    def preview_image(self, obj):
        if getattr(obj, "image", None):
            try:
                return format_html('<img src="{}" style="max-width:600px;border-radius:12px">', obj.image.url)
            except:
                pass
        return "Изображение не загружено"

    @admin.display(description="Промптов")
    def prompts_count(self, obj):
        if not obj.pk:
            return "—"
        count = obj.active_prompts_count
        return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count) if count > 0 else "0"


@admin.register(VideoPrompt)
class VideoPromptAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "short_prompt", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "category")
    search_fields = ("title", "prompt_text", "category__name")
    ordering = ("category__order", "order", "title")
    actions = (mark_active, mark_inactive)
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at",)

    @admin.display(description="Промпт")
    def short_prompt(self, obj):
        p = (obj.prompt_text or "").strip()
        return (p[:60] + "…") if len(p) > 60 else p


# ── Конфигурация видео моделей (расширенная) ─────────────────────
@admin.register(VideoModelConfiguration)
class VideoModelConfigurationAdmin(admin.ModelAdmin):
    form = VideoModelConfigurationForm
    list_display = (
        "name", "model_id", "category", "token_cost",
        "resolutions_count", "durations_count", "is_active",
        "is_beta", "is_premium", "order"
    )
    list_editable = ("is_active", "order", "token_cost")
    list_filter = ("is_active", "category", "is_beta", "is_premium", "provider")
    search_fields = ("name", "model_id", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category", "order", "name")
    actions = (mark_active, mark_inactive)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name", "model_id", "slug", "description",
                "category", "token_cost", "provider", "provider_version"
            ),
            "description": "Базовые параметры модели"
        }),
        ("Разрешения", {
            "fields": (
                "supports_custom_resolution",
                ("min_width", "max_width"),
                ("min_height", "max_height"),
                ("resolution_512x512", "resolution_512x768", "resolution_512x1024"),
                ("resolution_768x512", "resolution_768x768", "resolution_768x1024"),
                ("resolution_1024x512", "resolution_1024x768", "resolution_1024x1024"),
                ("resolution_1280x720", "resolution_1920x1080"),
                ("resolution_2560x1440", "resolution_3840x2160"),
            ),
            "classes": ("collapse",),
            "description": "Выберите доступные разрешения для этой модели"
        }),
        ("Соотношения сторон", {
            "fields": (
                # 🔲 Квадратные
                ("aspect_ratio_1_1",),
                # 📺 Классические (старые мониторы / ТВ)
                ("aspect_ratio_4_3", "aspect_ratio_3_2", "aspect_ratio_5_4"),
                # 🖥 Современные широкоэкранные
                ("aspect_ratio_16_9", "aspect_ratio_16_10", "aspect_ratio_15_9", "aspect_ratio_17_9"),
                # 🎬 Киноформаты
                ("aspect_ratio_1_85_1", "aspect_ratio_2_00_1", "aspect_ratio_2_20_1"),
                ("aspect_ratio_2_35_1", "aspect_ratio_2_39_1", "aspect_ratio_2_40_1"),
                # 🖥 Ультраширокие
                ("aspect_ratio_18_9", "aspect_ratio_19_9", "aspect_ratio_20_9"),
                ("aspect_ratio_21_9", "aspect_ratio_24_10", "aspect_ratio_32_9"),
                # 📱 Вертикальные (мобильные, соцсети)
                ("aspect_ratio_9_16", "aspect_ratio_3_4", "aspect_ratio_2_3"),
                ("aspect_ratio_4_5", "aspect_ratio_5_8", "aspect_ratio_10_16"),
                ("aspect_ratio_9_19_5", "aspect_ratio_9_20", "aspect_ratio_9_21"),
                # 🖼 Фотографические
                ("aspect_ratio_7_5", "aspect_ratio_8_10"),
            ),
            "classes": ("collapse",),
            "description": "Доступные соотношения сторон"
        }),
        ("Длительность", {
            "fields": (
                "supports_custom_duration",
                ("min_duration", "max_duration"),
                ("duration_2", "duration_3", "duration_4", "duration_5"),
                ("duration_6", "duration_8", "duration_10"),
                ("duration_15", "duration_20", "duration_30"),
            ),
            "classes": ("collapse",),
            "description": "Настройки длительности видео"
        }),
        ("Движение камеры", {
            "fields": (
                "supports_camera_movement",
                ("camera_static", "camera_pan_left", "camera_pan_right"),
                ("camera_tilt_up", "camera_tilt_down"),
                ("camera_zoom_in", "camera_zoom_out"),
                ("camera_dolly_in", "camera_dolly_out"),
                ("camera_orbit_left", "camera_orbit_right"),
                ("camera_crane_up", "camera_crane_down"),
            ),
            "classes": ("collapse",),
            "description": "Доступные типы движения камеры"
        }),
        ("Image-to-Video", {
            "fields": (
                "supports_image_to_video",
                "supports_motion_strength",
                ("min_motion_strength", "max_motion_strength", "default_motion_strength"),
            ),
            "classes": ("collapse",),
            "description": "Параметры для генерации видео из изображения"
        }),
        ("Продвинутые параметры", {
            "fields": (
                "supports_seed",
                "supports_negative_prompt",
                "supports_fps",
                ("min_fps", "max_fps", "default_fps"),
                "supports_guidance_scale",
                ("min_guidance_scale", "max_guidance_scale", "default_guidance_scale"),
                "supports_inference_steps",
                ("min_inference_steps", "max_inference_steps", "default_inference_steps"),
            ),
            "classes": ("collapse",),
            "description": "Дополнительные параметры генерации"
        }),
        ("Качество", {
            "fields": (
                "supports_quality",
                ("quality_low", "quality_medium"),
                ("quality_high", "quality_ultra"),
            ),
            "classes": ("collapse",),
            "description": "Уровни качества"
        }),
        ("Стилевые пресеты", {
            "fields": (
                "supports_style_presets",
                ("style_realistic", "style_anime", "style_cartoon"),
                ("style_cinematic", "style_artistic"),
            ),
            "classes": ("collapse",),
            "description": "Доступные стили"
        }),
        ("Форматы вывода", {
            "fields": (
                ("supports_mp4", "supports_webm", "supports_gif"),
                "supports_watermark_removal",
            ),
            "classes": ("collapse",),
            "description": "Поддерживаемые форматы"
        }),
        ("Метаданные", {
            "fields": (
                ("is_active", "is_beta", "is_premium"),
                "order",
            ),
            "description": "Статус и порядок отображения"
        }),
        ("Дополнительно", {
            "fields": (
                "admin_notes",
                ("created_at", "updated_at"),
            ),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Разрешений")
    def resolutions_count(self, obj):
        if not obj.pk:
            return "—"
        count = len(obj.get_available_resolutions())
        if count > 0:
            return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count)
        return "0"

    @admin.display(description="Длительностей")
    def durations_count(self, obj):
        if not obj.pk:
            return "—"
        count = len(obj.get_available_durations())
        if count > 0:
            return format_html('<span style="color:#10b981;font-weight:600">{}</span>', count)
        return "0"

    def save_model(self, request, obj, form, change):
        """Auto-generate slug if not provided"""
        if not obj.slug:
            from django.utils.text import slugify
            obj.slug = slugify(obj.name or "")[:120]
        super().save_model(request, obj, form, change)


# ── Aspect Ratio Quality Configurations ──────────────────────────────

class AspectRatioQualityConfigInline(admin.TabularInline):
    """
    Inline для редактирования конфигураций прямо в модели
    """
    model = AspectRatioQualityConfig
    extra = 1
    fields = ('aspect_ratio', 'quality', 'width', 'height', 'is_active', 'is_default', 'order', 'notes')
    ordering = ['order', 'aspect_ratio', 'quality']


@admin.register(AspectRatioQualityConfig)
class AspectRatioQualityConfigAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'model_info',
        'aspect_ratio',
        'quality',
        'dimensions_display',
        'megapixels_display',
        'is_default',
        'is_active',
        'order'
    )
    list_filter = ('model_type', 'quality', 'is_active', 'is_default')
    search_fields = ('aspect_ratio', 'notes')
    list_editable = ('is_active', 'is_default', 'order')
    ordering = ['model_type', 'model_id', 'order', 'aspect_ratio', 'quality']
    
    fieldsets = (
        ("Основная информация", {
            "fields": (
                ('model_type', 'model_id'),
                ('aspect_ratio', 'quality'),
            )
        }),
        ("Размеры (проверено на Runware)", {
            "fields": (
                ('width', 'height'),
            ),
            "description": "Точные размеры в пикселях, протестированные на Runware"
        }),
        ("Настройки", {
            "fields": (
                ('is_active', 'is_default'),
                'order',
                'notes',
            )
        }),
    )
    
    @admin.display(description="Модель")
    def model_info(self, obj):
        if obj.model_type == 'image':
            try:
                from .models_image import ImageModelConfiguration
                model = ImageModelConfiguration.objects.get(id=obj.model_id)
                return format_html(
                    '<span style="color:#3b82f6">📷 {}</span>',
                    model.name
                )
            except:
                return format_html('<span style="color:#ef4444">Image #{}</span>', obj.model_id)
        else:
            try:
                from .models_video import VideoModelConfiguration
                model = VideoModelConfiguration.objects.get(id=obj.model_id)
                return format_html(
                    '<span style="color:#8b5cf6">🎬 {}</span>',
                    model.name
                )
            except:
                return format_html('<span style="color:#ef4444">Video #{}</span>', obj.model_id)
    
    @admin.display(description="Размеры")
    def dimensions_display(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:600">{} × {}</span>',
            obj.width,
            obj.height
        )
    
    @admin.display(description="MP")
    def megapixels_display(self, obj):
        mp = obj.megapixels
        if mp >= 10:
            color = "#dc2626"  # red
        elif mp >= 5:
            color = "#f59e0b"  # orange
        else:
            color = "#10b981"  # green
        
        return format_html(
            '<span style="color:{};font-weight:600">{} MP</span>',
            color,
            mp
        )
    
    actions = [mark_active, mark_inactive]


@admin.register(AspectRatioPreset)
class AspectRatioPresetAdmin(admin.ModelAdmin):
    list_display = (
        'aspect_ratio',
        'name',
        'category',
        'icon',
        'is_common',
        'order'
    )
    list_filter = ('category', 'is_common')
    search_fields = ('aspect_ratio', 'name', 'description')
    list_editable = ('is_common', 'order')
    ordering = ['-is_common', 'order', 'aspect_ratio']
    
    fieldsets = (
        ("Основная информация", {
            "fields": (
                'aspect_ratio',
                'name',
                'category',
                'icon',
                'description',
            )
        }),
        ("Рекомендуемые размеры", {
            "fields": (
                ('recommended_sd', 'recommended_hd'),
                ('recommended_full_hd', 'recommended_2k'),
                ('recommended_4k', 'recommended_8k'),
            ),
            "description": "Примеры: 1920x1080, 3840x2160"
        }),
        ("Настройки", {
            "fields": (
                ('is_common', 'order'),
            )
        }),
    )
