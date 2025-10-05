from django import forms
from django.utils.html import strip_tags
import re
from .models import Category

BANNED_WORDS = {
    "script", "javascript", "onload", "onclick", "onerror", "alert", "eval",
    "<script", "</script", "<iframe", "</iframe", "vbscript", "activex"
}

def clean_text_content(text: str) -> str:
    """Очистка текста от потенциально опасного содержимого"""
    if not text:
        return ""

    text = strip_tags(text).strip()
    text_lower = text.lower()

    for banned in BANNED_WORDS:
        if banned in text_lower:
            raise forms.ValidationError(f"Недопустимое содержимое в тексте")

    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)

    return text[:500]


class ShareFromJobForm(forms.Form):
    title = forms.CharField(
        label="Заголовок",
        max_length=140,
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Заголовок (опционально)"}),
    )
    caption = forms.CharField(
        label="Подпись",
        max_length=240,
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Подпись (опционально)"}),
    )
    categories = forms.ModelMultipleChoiceField(
        label="Категории",
        required=False,
        queryset=Category.objects.none(),  # зададим в __init__
        widget=forms.SelectMultiple(attrs={"class": "input", "size": "6"}),
        help_text="Выберите одну или несколько категорий (создаёт админ).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.all()

    # Только «привести в порядок» строки
    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        return clean_text_content(title)[:140]

    def clean_caption(self):
        caption = (self.cleaned_data.get("caption") or "").strip()
        return clean_text_content(caption)[:240]


class PhotoCommentForm(forms.Form):
    text = forms.CharField(
        label="Комментарий",
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 3, "placeholder": "Напишите комментарий…"}),
    )

    def clean_text(self):
        tx = (self.cleaned_data.get("text") or "").strip()
        if not tx:
            raise forms.ValidationError("Комментарий не может быть пустым.")
        return clean_text_content(tx)[:1000]
