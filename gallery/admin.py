from __future__ import annotations

from django import forms
from django.contrib import admin
from .models import Category, PhotoComment
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
        'json_id', 'title', 'description', 'ratio', 'steps',
        'cfg', 'is_active', 'order', 'created_at'
    ]
    list_filter = ['is_active', 'ratio', 'created_at', 'updated_at']
    search_fields = ['title', 'description', 'prompt']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'json_id']

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'prompt', 'description', 'alt', 'image')
        }),
        ('Настройки генерации', {
            'fields': ('steps', 'cfg', 'ratio', 'seed')
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
