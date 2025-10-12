from __future__ import annotations

from django import forms
from django.contrib import admin
from .models import (
    Category,
    PhotoComment,
    PublicVideo,
    VideoComment,
    VideoLike,
    VideoCommentLike
)
from .models_slider import SliderExample

BANNED = {
    "nsfw", "nude", "nudity", "porn", "sex", "explicit", "xxx", "erotic",
}

def _sfw_check(text: str) -> None:
    low = (text or "").lower()
    if any(b in low for b in BANNED):
        raise forms.ValidationError("SFW only: обнаружены запрещённые слова.")


class ShareFromJobForm(forms.Form):
    title = forms.CharField(
        max_length=140, required=False,
        widget=forms.TextInput(attrs={
            "class": "input", "placeholder": "Короткий заголовок (до 140)"
        }),
        label="Заголовок",
    )
    caption = forms.CharField(
        max_length=240, required=False,
        widget=forms.TextInput(attrs={
            "class": "input", "placeholder": "Небольшая подпись (до 240)"
        }),
        label="Подпись",
    )
    # Разрешим выбрать одну или несколько — админ может заранее говорить «одна»,
    # но M2M в модели — значит позволим мультивыбор.
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "input", "size": "5"}),
        label="Категории",
    )

    def clean_title(self):
        t = self.cleaned_data.get("title", "").strip()
        if t:
            _sfw_check(t)
        return t

    def clean_caption(self):
        c = self.cleaned_data.get("caption", "").strip()
        if c:
            _sfw_check(c)
        return c


class PhotoCommentForm(forms.ModelForm):
    class Meta:
        model = PhotoComment
        fields = ("text",)
        widgets = {
            "text": forms.Textarea(attrs={
                "class": "textarea",
                "rows": 3,
                "placeholder": "Напишите комментарий…",
            })
        }
        labels = {"text": "Комментарий"}

    def clean_text(self):
        tx = (self.cleaned_data.get("text") or "").strip()
        if not tx:
            raise forms.ValidationError("Комментарий не может быть пустым.")
        _sfw_check(tx)
        return tx


@admin.register(SliderExample)
class SliderExampleAdmin(admin.ModelAdmin):
    """Админ-панель для управления примерами слайдера"""

    list_display = [
        'json_id', 'title', 'description', 'steps',
        'cfg', 'is_active', 'order', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'prompt']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'json_id']

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'prompt', 'description', 'alt', 'image')
        }),
        ('Настройки генерации', {
            'fields': ('steps', 'cfg', 'seed')
        }),
        ('Дополнительно', {
            'fields': ('order', 'is_active')
        }),
        ('Системная информация', {
            'fields': ('json_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['json_id', 'created_at', 'updated_at']

    actions = ['make_active', 'make_inactive', 'export_to_json']

    def make_active(self, request, queryset):
        """Активировать выбранные примеры"""
        count = queryset.update(is_active=True)
        SliderExample.export_to_json()
        self.message_user(request, f'Активировано примеров: {count}')
    make_active.short_description = "Активировать выбранные примеры"

    def make_inactive(self, request, queryset):
        """Деактивировать выбранные примеры"""
        count = queryset.update(is_active=False)
        SliderExample.export_to_json()
        self.message_user(request, f'Деактивировано примеров: {count}')
    make_inactive.short_description = "Деактивировать выбранные примеры"

    def export_to_json(self, request, queryset):
        """Экспорт в JSON файл"""
        success, message = SliderExample.export_to_json()
        if success:
            self.message_user(request, f'Экспорт завершен: {message}')
        else:
            self.message_user(request, f'Ошибка экспорта: {message}', level='ERROR')
    export_to_json.short_description = "Экспортировать в JSON файл"


@admin.register(PublicVideo)
class PublicVideoAdmin(admin.ModelAdmin):
    """Админ-панель для публичных видео"""
    list_display = ['id', 'title', 'uploaded_by', 'is_active', 'view_count', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'category']
    search_fields = ['title', 'caption', 'uploaded_by__username']
    list_editable = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['view_count', 'likes_count', 'comments_count', 'created_at']


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    """Админ-панель для комментариев к видео"""
    list_display = ['id', 'video', 'user', 'text_preview', 'is_visible', 'likes_count', 'created_at']
    list_filter = ['is_visible', 'created_at']
    search_fields = ['text', 'user__username', 'video__title']
    list_editable = ['is_visible']
    ordering = ['-created_at']

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Текст'


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    """Админ-панель для лайков видео"""
    list_display = ['id', 'video', 'user', 'session_key', 'created_at']
    list_filter = ['created_at']
    search_fields = ['video__title', 'user__username']
    ordering = ['-created_at']


@admin.register(VideoCommentLike)
class VideoCommentLikeAdmin(admin.ModelAdmin):
    """Админ-панель для лайков комментариев к видео"""
    list_display = ['id', 'comment', 'user', 'session_key', 'created_at']
    list_filter = ['created_at']
    ordering = ['-created_at']
