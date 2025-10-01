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
        return obj.suggestions.count()

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
    list_display = ("thumb", "title", "category", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("title", "prompt")
    list_filter = ("category", "is_active")
    ordering = ("category__name", "order", "-created_at")

    @admin.display(description="Превью")
    def thumb(self, obj):
        if getattr(obj, "image", None):
            return format_html('<img src="{}" style="height:40px;border-radius:4px">', obj.image.url)
        return "—"

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
