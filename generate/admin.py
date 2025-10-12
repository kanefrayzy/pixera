# generate/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    GenerationJob,
    Suggestion,
    SuggestionCategory,
    FreeGrant,
    ShowcaseCategory,
    ShowcaseImage,
    ShowcaseVideo,
    PromptCategory,
    CategoryPrompt,
    VideoModel,
    VideoPromptCategory,
    VideoPrompt,
)

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

# ── Остальные модели (как было) ─────────────────────────────────
@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "is_public", "is_trending", "created_at")
    list_filter = ("status", "is_public", "is_trending")
    search_fields = ("prompt", "user__username", "user__email")
    readonly_fields = ("created_at",)

@admin.register(FreeGrant)
class FreeGrantAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "gid", "fp", "total", "consumed", "left", "first_ip", "created_at")
    search_fields = ("gid", "fp", "user__username", "user__email", "first_ip")
    readonly_fields = ("created_at",)
    list_filter = ("user",)


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
@admin.register(VideoModel)
class VideoModelAdmin(admin.ModelAdmin):
    list_display = ("name", "model_id", "category", "token_cost", "max_duration", "is_active", "order")
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
        ("Настройки", {
            "fields": ("is_active", "order")
        }),
        ("Дополнительно", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
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
