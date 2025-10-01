# blog/admin.py
from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title", "is_published", "published_at", "created_at",
    )
    list_filter = ("is_published", "published_at", "created_at")
    search_fields = ("title", "excerpt", "body", "meta_title", "meta_description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Контент", {
            "fields": ("title", "slug", "cover", "excerpt", "body"),
        }),
        ("SEO", {
            "fields": (
                "meta_title", "meta_description",
                "og_title", "og_description", "og_image",
            )
        }),
        ("Публикация", {
            "fields": ("is_published", "published_at", "created_at", "updated_at"),
        }),
    )
